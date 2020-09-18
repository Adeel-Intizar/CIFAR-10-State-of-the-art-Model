# -*- coding: utf-8 -*-
"""CIFAR-10 Best.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/15Za3KniiBj-T8GbnfAiLrP0BolCP4w2E
"""

# Commented out IPython magic to ensure Python compatibility.
# %tensorflow_version 2.x
import tensorflow as tf
from tensorflow.keras.layers import Conv2D, Dense, BatchNormalization, MaxPooling2D, Dropout, Concatenate, add, multiply, GlobalAveragePooling2D
from tensorflow.keras.utils import plot_model
from tensorflow.keras.activations import sigmoid
from tensorflow.keras.datasets import cifar10
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import ModelCheckpoint, LearningRateScheduler, EarlyStopping
from tensorflow.keras.regularizers import l2
import numpy as np
from sklearn.model_selection import train_test_split

from tensorflow.keras import backend as K
from tensorflow.keras.utils import get_custom_objects
from tensorflow.keras.layers import Activation

class Mish(Activation):

  def __init__(self, activation, **kwargs):
    super(Mish, self).__init__(activation, **kwargs)
    self.__name__ = 'Mish'

def mish(x):
  return K.minimum(x * K.tanh(K.softplus(x)), 6)

get_custom_objects().update({'mish': Mish(mish)})

(train_images, train_labels), (test_images, test_labels) = cifar10.load_data()

def preprocess(x, l):
  def norm(x):
    mean = np.mean(x, axis=(0,1,2,3))
    std = np.std(x, axis=(0,1,2,3))
    x = (x - mean) / (std + 1e-7)
    return x

  x = norm(x)
  x = x.reshape(x.shape[0], x.shape[1], x.shape[2], x.shape[3])
  l = l.reshape(l.shape[0])
  return x, l

train_images, train_labels = preprocess(train_images, train_labels)
test_images, test_labels = preprocess(test_images, test_labels)

test_i, val_images, test_l, val_labels = train_test_split(test_images, test_labels, shuffle=True, random_state=42, stratify=test_labels)

print(train_images.shape)
print(train_labels.shape)
print(val_images.shape)
print(val_labels.shape)
print(test_i.shape)
print(test_l.shape)

def Block(x, f, k):
  if k == 1:
    pad = 'valid'
  else:
    pad = 'same'

  a = BatchNormalization(axis=3)(x)
  a = Conv2D(f, (k, k), use_bias=False, kernel_regularizer=l2(1e-3), padding=pad, kernel_initializer='he_uniform', activation='mish')(a)
  return a

def Inception(x, f):
  
  a = Block(x = x, f = f//8, k = 1)
  a1 = Block(x = a, f = f//2, k =1)
  a2 = Block(x = a, f = f//2, k = 3)
  a = Concatenate(axis=3)([a1, a2])
  a = Activation('mish')(a)

  b = GlobalAveragePooling2D()(a)
  b = Dense(f//16, kernel_regularizer=l2(1e-3), kernel_initializer='he_uniform', activation='mish')(b)
  b = Dense(f, kernel_regularizer=l2(1e-3), activation='sigmoid', kernel_initializer='he_uniform')(b)
  b = multiply([a, b])
  b = Activation('mish')(b)
  return b

def Residual(x, f):
  a = Block(x = x, f = f//8, k = 1)
  a1 = Block(x = a, f = f//2, k =1)
  a2 = Block(x = a, f = f//2, k = 3)
  a = Concatenate(axis=3)([a1, a2])
  a = add([x, a])
  a = Activation('mish')(a)

  b = GlobalAveragePooling2D()(a)
  b = Dense(f//16, kernel_regularizer=l2(1e-3), kernel_initializer='he_uniform', activation='mish')(b)
  b = Dense(f, kernel_regularizer=l2(1e-3), activation='sigmoid', kernel_initializer='he_uniform')(b)
  b = multiply([a, b])
  b = add([a, b])
  b = Activation('mish')(b)
  return b

def Mod():
  inp = tf.keras.Input(shape=(32, 32, 3))

  x = BatchNormalization(axis=3)(inp)
  x = Conv2D(96, (3,3), padding='same', use_bias=False, kernel_regularizer=l2(1e-3), kernel_initializer='he_uniform', activation='mish')(x)

  x = Inception(x, 192)
  x = Residual(x, 192)
  x = Inception(x, 288)
  x = Residual(x, 288)
  x = Inception(x, 384)
  x = Residual(x, 384)
  x = MaxPooling2D()(x)
  x = Dropout(0.2)(x)

  x = Inception(x, 480)
  x = Residual(x, 480)
  x = Inception(x, 576)
  x = Residual(x, 576)
  x = Inception(x, 672)
  x = Residual(x, 672)
  x = MaxPooling2D()(x)
  x = Dropout(0.3)(x)

  x = BatchNormalization(axis=3)(x)
  x = Conv2D(816, (1,1), use_bias=False, kernel_regularizer=l2(1e-3), kernel_initializer='he_uniform', activation='mish')(x)

  x = GlobalAveragePooling2D()(x)
  x = Dropout(0.4)(x)
  x = Dense(10, activation='softmax')(x)

  return tf.keras.Model(inp, x, name='ElNet')

model = Mod()
model.summary()

datagen = ImageDataGenerator(
    rotation_range=10,
    width_shift_range = 0.1,
    height_shift_range = 0.1,
    horizontal_flip = True
    )
datagen.fit(train_images)

def step(epoch):
  if epoch < 10:
    return 0.01
  elif epoch < 20:
    return 0.001
  elif epoch < 25:
    return 0.0001
  elif epoch < 30:
    return 0.00001
  else:
    return 0.000001

lrate = LearningRateScheduler(step, verbose=0)
checkpoint = ModelCheckpoint('CheckPoint_Model.h5', save_best_only=True, verbose=0, monitor='val_acc')

model.compile(loss = 'sparse_categorical_crossentropy', 
              optimizer = tf.keras.optimizers.SGD(lr = 0.001, momentum=0.9, nesterov=True),
              metrics = ['acc'])

batch_size = 50
his = model.fit(datagen.flow(train_images, train_labels, batch_size=32), 
                steps_per_epoch = 5*(len(train_images)//batch_size), epochs = 40, verbose=1, callbacks=[checkpoint, lrate], 
                validation_data = (val_images, val_labels))

loss, acc = model.evaluate(train_images, train_labels, verbose=0)
print(f'Training Loss: {loss:.3} \t Training Acc: {acc:.3}')

loss, acc = model.evaluate(val_images, val_labels, verbose=0)
print(f'Validation Loss: {loss:.3} \t Validation Acc: {acc:.3}')

loss, acc = model.evaluate(test_images, test_labels, verbose=0)
print(f'Testing Loss: {loss:.3} \t Testing Acc: {acc:.3}')

clf = tf.keras.models.load_model('CheckPoint_Model.h5', custom_objects={'Mish': Mish(mish)})

loss, acc = clf.evaluate(train_images, train_labels, verbose=0)
print(f'Training Loss: {loss:.3} \t Training Acc: {acc:.3}')

loss, acc = clf.evaluate(val_images, val_labels, verbose=0)
print(f'Validation Loss: {loss:.3} \t Validation Acc: {acc:.3}')

loss, acc = clf.evaluate(test_i, test_l, verbose=0)
print(f'Testing Loss: {loss:.3} \t Testing Acc: {acc:.3}')

clf.save_weights('Model_Weights_94%.h5')

json = clf.to_json()
with open('Model-94.json', 'w') as json_f:
  json_f.write(json)
  print('Json Loaded')

yaml = model.to_yaml()
with open('Model-94.yaml', 'w') as yaml_f:
  yaml_f.write(yaml)
  print('Yaml Loaded')

