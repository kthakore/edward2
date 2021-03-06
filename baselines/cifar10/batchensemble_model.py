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

"""ResNet32 model for Keras adapted from tf.keras.applications.ResNet50.

# Reference:
- [Deep Residual Learning for Image Recognition](
    https://arxiv.org/abs/1512.03385)
Adapted from code contributed by BigMoyan.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import edward2 as ed
import tensorflow.compat.v2 as tf


def ensemble_resnet_layer(inputs,
                          filters=16,
                          kernel_size=3,
                          strides=1,
                          num_models=1,
                          random_sign_init=1.0,
                          activation='relu',
                          dropout_rate=0.,
                          l2=0.):
  """BatchEnsemble 2D Convolution-Batch Normalization-Activation stack builder.

  Args:
    inputs: tf.Tensor.
    filters: Number of filters for Conv2D.
    kernel_size: Kernel dimensions for Conv2D.
    strides: Stride dimensinons for Conv2D.
    num_models: Number of ensemble members.
    random_sign_init: Probability of 1 in random sign init.
    activation: tf.keras.activations.Activation.
    dropout_rate: Dropout rate.
    l2: L2 regularization coefficient.

  Returns:
    tf.Tensor.
  """
  if random_sign_init > 0:
    alpha_initializer = ed.initializers.RandomSign(random_sign_init)
    gamma_initializer = ed.initializers.RandomSign(random_sign_init)
  else:
    alpha_initializer = tf.keras.initializers.RandomNormal(
        mean=1.0, stddev=-random_sign_init)
    gamma_initializer = tf.keras.initializers.RandomNormal(
        mean=1.0, stddev=-random_sign_init)

  x = inputs
  if dropout_rate > 0:
    x = tf.keras.layers.Dropout(dropout_rate)(x, training=True)
  x = ed.layers.BatchEnsembleConv2D(
      filters,
      kernel_size=kernel_size,
      alpha_initializer=alpha_initializer,
      gamma_initializer=gamma_initializer,
      strides=strides,
      padding='same',
      use_bias=False,
      kernel_initializer='he_normal',
      kernel_regularizer=tf.keras.regularizers.l2(l2),
      bias_regularizer=tf.keras.regularizers.l2(l2),
      num_models=num_models)(x)
  x = tf.keras.layers.BatchNormalization(epsilon=1e-5,
                                         momentum=0.9)(x)
  if activation is not None:
    x = tf.keras.layers.Activation(activation)(x)
  return x


def ensemble_resnet_v1(input_shape,
                       depth,
                       num_classes,
                       width_multiplier,
                       num_models,
                       random_sign_init,
                       dropout_rate,
                       l2):
  """Builds BatchEnsemble ResNet v1.

  Args:
    input_shape: tf.Tensor.
    depth: ResNet depth.
    num_classes: Number of output classes.
    width_multiplier: Integer to multiply the number of typical filters by.
    num_models: Number of ensemble members.
    random_sign_init: probability of RandomSign initializer.
    dropout_rate: Dropout rate.
    l2: L2 regularization coefficient.

  Returns:
    tf.keras.Model.
  """
  if (depth - 2) % 6 != 0:
    raise ValueError('depth should be 6n+2 (e.g., 20, 32, 44).')
  filters = 16 * width_multiplier
  num_res_blocks = int((depth - 2) / 6)

  if random_sign_init > 0:
    alpha_initializer = ed.initializers.RandomSign(random_sign_init)
    gamma_initializer = ed.initializers.RandomSign(random_sign_init)
  else:
    alpha_initializer = tf.keras.initializers.RandomNormal(
        mean=1.0, stddev=-random_sign_init)
    gamma_initializer = tf.keras.initializers.RandomNormal(
        mean=1.0, stddev=-random_sign_init)

  inputs = tf.keras.layers.Input(shape=input_shape)
  x = ensemble_resnet_layer(inputs,
                            filters=filters,
                            num_models=num_models,
                            random_sign_init=random_sign_init,
                            l2=l2)
  for stack in range(3):
    for res_block in range(num_res_blocks):
      strides = 1
      if stack > 0 and res_block == 0:  # first layer but not first stack
        strides = 2  # downsample
      y = ensemble_resnet_layer(x,
                                filters=filters,
                                strides=strides,
                                num_models=num_models,
                                random_sign_init=random_sign_init,
                                dropout_rate=dropout_rate,
                                l2=l2)
      y = ensemble_resnet_layer(y,
                                filters=filters,
                                activation=None,
                                num_models=num_models,
                                random_sign_init=random_sign_init,
                                dropout_rate=dropout_rate,
                                l2=l2)
      if stack > 0 and res_block == 0:  # first layer but not first stack
        # linear projection residual shortcut connection to match
        # changed dims
        x = ensemble_resnet_layer(x,
                                  filters=filters,
                                  kernel_size=1,
                                  strides=strides,
                                  activation=None,
                                  num_models=num_models,
                                  random_sign_init=random_sign_init,
                                  dropout_rate=dropout_rate,
                                  l2=l2)
      x = tf.keras.layers.add([x, y])
      x = tf.keras.layers.Activation('relu')(x)
    filters *= 2

  # v1 does not use BN after last shortcut connection-ReLU
  x = tf.keras.layers.AveragePooling2D(pool_size=8)(x)
  x = tf.keras.layers.Flatten()(x)
  if dropout_rate > 0.:
    x = tf.keras.layers.Dropout(dropout_rate)(x, training=True)
  x = ed.layers.BatchEnsembleDense(
      num_classes,
      alpha_initializer=alpha_initializer,
      gamma_initializer=gamma_initializer,
      activation=None,
      kernel_initializer='he_normal',
      kernel_regularizer=tf.keras.regularizers.l2(l2),
      bias_regularizer=tf.keras.regularizers.l2(l2),
      num_models=num_models)(x)
  model = tf.keras.Model(inputs=inputs, outputs=x)
  return model
