# coding=utf-8
# Copyright 2019 The Edward2 Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ResNet50 model for Keras.

Adapted from tf.keras.applications.resnet50.ResNet50().
and //third_party/cloud_tpu/models/resnet50_keras.

Related papers/blogs:
- https://arxiv.org/abs/1512.03385
- https://arxiv.org/pdf/1603.05027v2.pdf
- http://torch.ch/blog/2016/02/04/resnets.html

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow.compat.v2 as tf

# Use batch normalization defaults from Pytorch.
BATCH_NORM_DECAY = 0.9
BATCH_NORM_EPSILON = 1e-5


def identity_block(input_tensor, kernel_size, filters, stage, block):
  """The identity block is the block that has no conv layer at shortcut.

  Args:
    input_tensor: tf.Tensor.
    kernel_size: default 3, the kernel size of
        middle conv layer at main path
    filters: list of integers, the filters of 3 conv layer at main path
    stage: integer, current stage label, used for generating layer names
    block: 'a','b'..., current block label, used for generating layer names

  Returns:
    tf.Tensor.
  """
  filters1, filters2, filters3 = filters
  if tf.keras.backend.image_data_format() == 'channels_last':
    bn_axis = 3
  else:
    bn_axis = 1
  conv_name_base = 'res' + str(stage) + block + '_branch'
  bn_name_base = 'bn' + str(stage) + block + '_branch'

  x = tf.keras.layers.Conv2D(
      filters1, (1, 1),
      use_bias=False,
      kernel_initializer='he_normal',
      name=conv_name_base + '2a')(input_tensor)
  x = tf.keras.layers.BatchNormalization(
      axis=bn_axis,
      momentum=BATCH_NORM_DECAY,
      epsilon=BATCH_NORM_EPSILON,
      name=bn_name_base + '2a')(x)
  x = tf.keras.layers.Activation('relu')(x)

  x = tf.keras.layers.Conv2D(
      filters2, kernel_size,
      use_bias=False,
      padding='same',
      kernel_initializer='he_normal',
      name=conv_name_base + '2b')(x)
  x = tf.keras.layers.BatchNormalization(
      axis=bn_axis,
      momentum=BATCH_NORM_DECAY,
      epsilon=BATCH_NORM_EPSILON,
      name=bn_name_base + '2b')(x)
  x = tf.keras.layers.Activation('relu')(x)

  x = tf.keras.layers.Conv2D(
      filters3, (1, 1),
      use_bias=False,
      kernel_initializer='he_normal',
      name=conv_name_base + '2c')(x)
  x = tf.keras.layers.BatchNormalization(
      axis=bn_axis,
      momentum=BATCH_NORM_DECAY,
      epsilon=BATCH_NORM_EPSILON,
      name=bn_name_base + '2c')(x)

  x = tf.keras.layers.add([x, input_tensor])
  x = tf.keras.layers.Activation('relu')(x)
  return x


def conv_block(input_tensor,
               kernel_size,
               filters,
               stage,
               block,
               strides=(2, 2)):
  """A block that has a conv layer at shortcut.

  Note that strides appear in the second conv (3x3) rather than the first (1x1).
  This is also known as "ResNet v1.5" as it differs from He et al. (2015)
  (http://torch.ch/blog/2016/02/04/resnets.html).

  Args:
    input_tensor: tf.Tensor.
    kernel_size: Kernel size of middle conv layer at main path.
    filters: list of integers, the filters of 3 conv layer at main path
    stage: integer, current stage label, used for generating layer names
    block: 'a','b'..., current block label, used for generating layer names
    strides: Strides for the second conv layer in the block.

  Returns:
    tf.Tensor.
  """
  filters1, filters2, filters3 = filters
  if tf.keras.backend.image_data_format() == 'channels_last':
    bn_axis = 3
  else:
    bn_axis = 1
  conv_name_base = 'res' + str(stage) + block + '_branch'
  bn_name_base = 'bn' + str(stage) + block + '_branch'

  x = tf.keras.layers.Conv2D(
      filters1, (1, 1),
      use_bias=False,
      kernel_initializer='he_normal',
      name=conv_name_base + '2a')(input_tensor)
  x = tf.keras.layers.BatchNormalization(
      axis=bn_axis,
      momentum=BATCH_NORM_DECAY,
      epsilon=BATCH_NORM_EPSILON,
      name=bn_name_base + '2a')(x)
  x = tf.keras.layers.Activation('relu')(x)

  x = tf.keras.layers.Conv2D(
      filters2, kernel_size,
      strides=strides,
      padding='same',
      use_bias=False,
      kernel_initializer='he_normal',
      name=conv_name_base + '2b')(x)
  x = tf.keras.layers.BatchNormalization(
      axis=bn_axis,
      momentum=BATCH_NORM_DECAY,
      epsilon=BATCH_NORM_EPSILON,
      name=bn_name_base + '2b')(x)
  x = tf.keras.layers.Activation('relu')(x)

  x = tf.keras.layers.Conv2D(
      filters3, (1, 1),
      use_bias=False,
      kernel_initializer='he_normal',
      name=conv_name_base + '2c')(x)
  x = tf.keras.layers.BatchNormalization(
      axis=bn_axis,
      momentum=BATCH_NORM_DECAY,
      epsilon=BATCH_NORM_EPSILON,
      name=bn_name_base + '2c')(x)

  shortcut = tf.keras.layers.Conv2D(
      filters3, (1, 1),
      use_bias=False,
      strides=strides,
      kernel_initializer='he_normal',
      name=conv_name_base + '1')(input_tensor)
  shortcut = tf.keras.layers.BatchNormalization(
      axis=bn_axis,
      momentum=BATCH_NORM_DECAY,
      epsilon=BATCH_NORM_EPSILON,
      name=bn_name_base + '1')(shortcut)

  x = tf.keras.layers.add([x, shortcut])
  x = tf.keras.layers.Activation('relu')(x)
  return x


def resnet50(num_classes):
  """Builds ResNet50.

  Args:
    num_classes: Number of output classes.

  Returns:
    tf.keras.Model.
  """
  if tf.keras.backend.image_data_format() == 'channels_first':
    input_shape = (3, 224, 224)
    bn_axis = 1
  else:
    input_shape = (224, 224, 3)
    bn_axis = 3

  img_input = tf.keras.layers.Input(shape=input_shape)
  x = tf.keras.layers.ZeroPadding2D(padding=(3, 3), name='conv1_pad')(img_input)
  x = tf.keras.layers.Conv2D(
      64, (7, 7),
      use_bias=False,
      strides=(2, 2),
      padding='valid',
      kernel_initializer='he_normal',
      name='conv1')(x)
  x = tf.keras.layers.BatchNormalization(
      axis=bn_axis,
      momentum=BATCH_NORM_DECAY,
      epsilon=BATCH_NORM_EPSILON,
      name='bn_conv1')(x)
  x = tf.keras.layers.Activation('relu')(x)
  x = tf.keras.layers.MaxPooling2D((3, 3), strides=(2, 2), padding='same')(x)

  x = conv_block(x, 3, [64, 64, 256], stage=2, block='a', strides=(1, 1))
  x = identity_block(x, 3, [64, 64, 256], stage=2, block='b')
  x = identity_block(x, 3, [64, 64, 256], stage=2, block='c')

  x = conv_block(x, 3, [128, 128, 512], stage=3, block='a')
  x = identity_block(x, 3, [128, 128, 512], stage=3, block='b')
  x = identity_block(x, 3, [128, 128, 512], stage=3, block='c')
  x = identity_block(x, 3, [128, 128, 512], stage=3, block='d')

  x = conv_block(x, 3, [256, 256, 1024], stage=4, block='a')
  x = identity_block(x, 3, [256, 256, 1024], stage=4, block='b')
  x = identity_block(x, 3, [256, 256, 1024], stage=4, block='c')
  x = identity_block(x, 3, [256, 256, 1024], stage=4, block='d')
  x = identity_block(x, 3, [256, 256, 1024], stage=4, block='e')
  x = identity_block(x, 3, [256, 256, 1024], stage=4, block='f')

  x = conv_block(x, 3, [512, 512, 2048], stage=5, block='a')
  x = identity_block(x, 3, [512, 512, 2048], stage=5, block='b')
  x = identity_block(x, 3, [512, 512, 2048], stage=5, block='c')

  x = tf.keras.layers.GlobalAveragePooling2D(name='avg_pool')(x)
  x = tf.keras.layers.Dense(
      num_classes,
      activation='softmax',
      kernel_initializer=tf.keras.initializers.RandomNormal(stddev=0.01),
      name='fc1000')(x)
  return tf.keras.models.Model(img_input, x, name='resnet50')