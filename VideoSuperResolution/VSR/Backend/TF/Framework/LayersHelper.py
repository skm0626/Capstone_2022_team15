"""
Copyright: Wenyi Tang 2017-2020
Author: Wenyi Tang
Email: wenyi.tang@intel.com
Created Date: Sep 5th 2018

commonly used layers helper
"""

from VSR.Util import to_list
from .. import tf
from ..Util import (
  SpectralNorm, TorchInitializer, pixel_shift, pop_dict_wo_keyerror, prelu
)


class Layers(object):
  def batch_norm(self, x, training, decay=0.9, epsilon=1e-5, name=None):
    # interesting.
    return tf.layers.batch_normalization(x,
                                         momentum=decay,
                                         training=training,
                                         fused=False,
                                         epsilon=epsilon,
                                         name=name)

  def instance_norm(self, x, trainable=True, name=None, reuse=None):
    from .. import tfc
    with tf.variable_scope(name, 'InstanceNorm', reuse=reuse):
      return tfc.layers.instance_norm(
          x,
          trainable=trainable,
          variables_collections=[tf.GraphKeys.GLOBAL_VARIABLES])

  def layer_norm(self, x, trainable=True, name=None, reuse=None):
    from .. import tfc
    with tf.variable_scope(name, 'LayerNorm', reuse=reuse):
      return tfc.layers.layer_norm(
          x,
          trainable=trainable,
          variables_collections=[tf.GraphKeys.GLOBAL_VARIABLES])

  def group_norm(self, x, group, axis, trainable=True, name=None, reuse=None):
    from .. import tfc
    with tf.variable_scope(name, 'GroupNorm', reuse=reuse):
      return tfc.layers.group_norm(
          x, group, axis,
          trainable=trainable,
          variables_collections=[tf.GraphKeys.GLOBAL_VARIABLES])

  def conv2d(self, x, filters, kernel_size, strides=(1, 1), padding='same',
             data_format='channels_last', dilation_rate=(1, 1),
             activation=None, use_bias=True, use_batchnorm=False,
             use_sn=False, use_in=False, use_ln=False, use_gn=False,
             kernel_initializer='he_normal',
             kernel_regularizer='l2', **kwargs):
    """wrap a convolution for common use case"""

    if kernel_initializer == 'torch':
      ki = TorchInitializer()
      kr = None
      if use_bias:
        bi = TorchInitializer(kernel_size * kernel_size * x.shape[-1])
      else:
        bi = tf.zeros_initializer()
    else:
      ki, kr = self._kernel(kernel_initializer, kernel_regularizer)
      bi = tf.zeros_initializer()
    nn = tf.layers.Conv2D(filters, kernel_size, strides=strides,
                          padding=padding, data_format=data_format,
                          dilation_rate=dilation_rate, use_bias=use_bias,
                          kernel_initializer=ki, kernel_regularizer=kr,
                          bias_initializer=bi, **kwargs)
    nn.build(x.shape.as_list())
    if use_sn:
      nn.kernel = SpectralNorm()(nn.kernel)
    x = nn(x)
    if use_batchnorm:
      x = tf.layers.batch_normalization(x, training=self.training_phase)
    if use_in:
      x = self.instance_norm(x)
    if use_ln:
      x = self.layer_norm(x)
    if use_gn:
      x = self.group_norm(x, 32, -1)
    activator = self._act(activation)
    if activation:
      x = activator(x)
    return x

  def conv3d(self, x, filters, kernel_size, strides=(1, 1, 1), padding='same',
             data_format='channels_last', dilation_rate=(1, 1, 1),
             activation=None, use_bias=True, use_batchnorm=False,
             use_in=False, use_ln=False, use_gn=False,
             kernel_initializer='he_normal', kernel_regularizer='l2',
             **kwargs):

    if kernel_initializer == 'torch':
      ki = TorchInitializer()
      kr = None
      if use_bias:
        bi = TorchInitializer(kernel_size * kernel_size * x.shape[-1])
      else:
        bi = tf.zeros_initializer()
    else:
      ki, kr = self._kernel(kernel_initializer, kernel_regularizer)
      bi = tf.zeros_initializer()
    nn = tf.layers.Conv3D(filters, kernel_size, strides=strides,
                          padding=padding, data_format=data_format,
                          dilation_rate=dilation_rate, use_bias=use_bias,
                          kernel_initializer=ki, kernel_regularizer=kr,
                          bias_initializer=bi, **kwargs)
    nn.build(x.shape.as_list())
    x = nn(x)
    if use_batchnorm:
      x = tf.layers.batch_normalization(x, training=self.training_phase)
    if use_in:
      x = self.instance_norm(x)
    if use_ln:
      x = self.layer_norm(x)
    if use_gn:
      x = self.group_norm(x, 32, -1)
    activator = self._act(activation)
    if activation:
      x = activator(x)
    return x

  def deconv2d(self, x,
               filters,
               kernel_size,
               strides=(1, 1),
               padding='same',
               data_format='channels_last',
               activation=None,
               use_bias=True,
               use_batchnorm=False,
               use_sn=False,
               use_in=False,
               use_ln=False,
               use_gn=False,
               kernel_initializer='he_normal',
               kernel_regularizer='l2',
               **kwargs):
    """warp a conv2d_transpose op for simplicity usage"""

    if kernel_initializer == 'torch':
      ki = TorchInitializer()
      kr = None
      if use_bias:
        bi = TorchInitializer(kernel_size * kernel_size * x.shape[-1])
      else:
        bi = tf.zeros_initializer()
    else:
      ki, kr = self._kernel(kernel_initializer, kernel_regularizer)
      bi = tf.zeros_initializer()
    nn = tf.layers.Conv2DTranspose(filters, kernel_size, strides=strides,
                                   padding=padding,
                                   data_format=data_format,
                                   use_bias=use_bias,
                                   bias_initializer=bi,
                                   kernel_initializer=ki,
                                   kernel_regularizer=kr, **kwargs)
    nn.build(x.shape.as_list())
    if use_sn:
      nn.kernel = SpectralNorm()(nn.kernel)
    x = nn(x)
    if use_batchnorm:
      x = tf.layers.batch_normalization(x, training=self.training_phase)
    if use_in:
      x = self.instance_norm(x)
    if use_ln:
      x = self.layer_norm(x)
    if use_gn:
      x = self.group_norm(x, 32, -1)
    activator = self._act(activation)
    if activation:
      x = activator(x)
    return x

  def deconv3d(self, x,
               filters,
               kernel_size,
               strides=(1, 1, 1),
               padding='same',
               data_format='channels_last',
               activation=None,
               use_bias=True,
               use_batchnorm=False,
               use_in=False,
               use_ln=False,
               use_gn=False,
               kernel_initializer='he_normal',
               kernel_regularizer='l2',
               **kwargs):

    if kernel_initializer == 'torch':
      ki = TorchInitializer()
      kr = None
      if use_bias:
        bi = TorchInitializer(kernel_size * kernel_size * x.shape[-1])
      else:
        bi = tf.zeros_initializer()
    else:
      ki, kr = self._kernel(kernel_initializer, kernel_regularizer)
      bi = tf.zeros_initializer()
    nn = tf.layers.Conv3DTranspose(filters, kernel_size, strides=strides,
                                   padding=padding,
                                   data_format=data_format,
                                   use_bias=use_bias,
                                   bias_initializer=bi,
                                   kernel_initializer=ki,
                                   kernel_regularizer=kr, **kwargs)
    nn.build(x.shape.as_list())
    x = nn(x)
    if use_batchnorm:
      x = tf.layers.batch_normalization(x, training=self.training_phase)
    if use_in:
      x = self.instance_norm(x)
    if use_ln:
      x = self.layer_norm(x)
    if use_gn:
      x = self.group_norm(x, 32, -1)
    activator = self._act(activation)
    if activation:
      x = activator(x)
    return x

  def dense(self, x, units, activation=None, use_bias=True, use_sn=False,
            kernel_initializer='he_normal', kernel_regularizer='l2',
            **kwargs):
    act = self._act(activation)
    ki, kr = self._kernel(kernel_initializer, kernel_regularizer)
    nn = tf.layers.Dense(units, use_bias=use_bias,
                         kernel_initializer=ki,
                         kernel_regularizer=kr, **kwargs)
    nn.build(x.shape.as_list())
    if use_sn:
      nn.kernel = SpectralNorm()(nn.kernel)
    x = nn(x)
    if act:
      x = act(x)
    return x

  linear = dense

  @staticmethod
  def _act(activation):
    activator = None
    if activation:
      if isinstance(activation, str):
        if activation == 'relu':
          activator = tf.nn.relu
        elif activation == 'tanh':
          activator = tf.nn.tanh
        elif activation == 'prelu':
          activator = prelu
        elif activation == 'lrelu':
          activator = tf.nn.leaky_relu
      elif callable(activation):
        activator = activation
      else:
        raise ValueError('invalid activation!')
    return activator

  def _kernel(self, kernel_initializer, kernel_regularizer):
    ki = None
    if isinstance(kernel_initializer, str):
      if kernel_initializer == 'he_normal':
        ki = tf.keras.initializers.he_normal()
      elif kernel_initializer == 'he_uniform':
        ki = tf.keras.initializers.he_uniform()
      elif kernel_initializer == 'zeros' or kernel_initializer == 'zero':
        ki = tf.keras.initializers.zeros()
      elif 'truncated_normal' in kernel_initializer:
        stddev = float(kernel_initializer.split('_')[-1])
        ki = tf.truncated_normal_initializer(stddev=stddev)
      elif 'random_normal' in kernel_initializer:
        stddev = float(kernel_initializer.split('_')[-1])
        ki = tf.random_normal_initializer(stddev=stddev)
    elif callable(kernel_initializer):
      ki = kernel_initializer
    elif kernel_initializer:
      raise ValueError('invalid kernel initializer!')
    kr = None
    if isinstance(kernel_regularizer, str):
      if kernel_regularizer == 'l1':
        kr = tf.keras.regularizers.l1(
            self.weight_decay) if self.weight_decay else None
      elif kernel_regularizer == 'l2':
        kr = tf.keras.regularizers.l2(
            self.weight_decay) if self.weight_decay else None
    elif callable(kernel_regularizer):
      kr = kernel_regularizer
    elif kernel_regularizer:
      raise ValueError('invalid kernel regularizer!')
    return ki, kr

  def upscale(self, image, method='espcn', scale=None, direct_output=True,
              **kwargs):
    """Image up-scale layer

    Upsample `image` width and height by scale factor `scale[0]` and
    `scale[1]`. Perform upsample progressively: i.e. x12:= x2->x2->x3

    Args:
        image: tensors to upsample
        method: method could be 'espcn', 'nearest' or 'deconv'
        scale: None or int or [int, int]. If None, `scale`=`self.scale`
        direct_output: output channel is the desired RGB or Grayscale, if
          False, keep the same channels as `image`
    """
    _allowed_method = ('espcn', 'nearest', 'deconv')
    assert str(method).lower() in _allowed_method
    method = str(method).lower()
    act = kwargs.get('activator')
    ki = kwargs.get('kernel_initializer', 'he_normal')
    kr = kwargs.get('kernel_regularizer', 'l2')
    use_bias = kwargs.get('use_bias', True)

    scale_x, scale_y = to_list(scale, 2) or self.scale
    features = self.channel if direct_output else image.shape.as_list()[-1]
    while scale_x > 1 or scale_y > 1:
      if scale_x % 2 == 1 or scale_y % 2 == 1:
        if method == 'espcn':
          image = pixel_shift(self.conv2d(
              image, features * scale_x * scale_y, 3,
              use_bias=use_bias, kernel_initializer=ki, kernel_regularizer=kr),
              [scale_x, scale_y], features)
        elif method == 'nearest':
          image = pixel_shift(
              tf.concat([image] * scale_x * scale_y, -1),
              [scale_x, scale_y],
              image.shape[-1])
        elif method == 'deconv':
          image = self.deconv2d(image, features, 3,
                                strides=[scale_y, scale_x],
                                kernel_initializer=ki,
                                kernel_regularizer=kr,
                                use_bias=use_bias)
        if act:
          image = act(image)
        break
      else:
        scale_x //= 2
        scale_y //= 2
        if method == 'espcn':
          image = pixel_shift(self.conv2d(
              image, features * 4, 3, use_bias=use_bias,
              kernel_initializer=ki, kernel_regularizer=kr), [2, 2], features)
        elif method == 'nearest':
          image = pixel_shift(
              tf.concat([image] * 4, -1),
              [2, 2],
              image.shape[-1])
        elif method == 'deconv':
          image = self.deconv2d(image, features, 3, strides=2,
                                use_bias=use_bias,
                                kernel_initializer=ki, kernel_regularizer=kr)
        if act:
          image = act(image)
    return image

  def __getattr__(self, item):
    from functools import partial as _p
    """Make an alignment for easy calls. You can add more patterns as below.
    
    >>> Layers.relu_conv2d = Layers.conv2d(activation='relu')
    >>> Layers.bn_conv2d = Layers.conv2d(use_batchnorm=True)
    >>> Layers.sn_leaky_conv2d = Layers.conv2d(use_sn=True, activation='lrelu')
    
    NOTE: orders do not matter.
    """
    if 'conv2d' in item:
      items = item.split('_')
      kwargs = {
        'kernel_initializer': 'he_normal',
        'kernel_regularizer': 'l2',
        'use_batchnorm': False,
        'use_sn': False,
      }
      if 'bn' in items or 'batchnorm' in items:
        kwargs.update(use_batchnorm=True)
      if 'sn' in items or 'spectralnorm' in items:
        kwargs.update(use_sn=True)
      if 'relu' in items:
        kwargs.update(activation='relu')
      if 'leaky' in items or 'lrelu' in items or 'leakyrelu' in items:
        kwargs.update(activation='lrelu')
      if 'prelu' in items:
        kwargs.update(activation='prelu')
      if 'tanh' in items:
        kwargs.update(activation='tanh')
      return _p(self.conv2d, **kwargs)
    elif 'conv3d' in item:
      items = item.split('_')
      kwargs = {
        'kernel_initializer': 'he_normal',
        'kernel_regularizer': 'l2',
        'use_batchnorm': False,
      }
      if 'bn' in items or 'batchnorm' in items:
        kwargs.update(use_batchnorm=True)
      if 'relu' in items:
        kwargs.update(activation='relu')
      if 'leaky' in items or 'lrelu' in items or 'leakyrelu' in items:
        kwargs.update(activation='lrelu')
      if 'prelu' in items:
        kwargs.update(activation='prelu')
      if 'tanh' in items:
        kwargs.update(activation='tanh')
      return _p(self.conv3d, **kwargs)
    elif 'dense' in item or 'linear' in item:
      items = item.split('_')
      kwargs = {
        'kernel_initializer': 'he_normal',
        'kernel_regularizer': 'l2',
        'use_sn': False,
      }
      if 'sn' in items or 'spectralnorm' in items:
        kwargs.update(use_sn=True)
      if 'relu' in items:
        kwargs.update(activation='relu')
      if 'leaky' in items or 'lrelu' in items or 'leakyrelu' in items:
        kwargs.update(activation='lrelu')
      if 'prelu' in items:
        kwargs.update(activation='prelu')
      if 'tanh' in items:
        kwargs.update(activation='tanh')
      return _p(self.dense, **kwargs)

    return None

  def resblock(self, x, filters, kernel_size, strides=(1, 1), padding='same',
               data_format='channels_last', activation=None, use_bias=True,
               use_batchnorm=False, use_sn=False,
               kernel_initializer='he_normal',
               kernel_regularizer='l2', placement=None, **kwargs):
    """make a residual block

    Args:
        x:
        filters:
        kernel_size:
        strides: if strides is more than 1, resblock downsample in the 2nd
          conv, and the short cut 1x1 conv
        padding:
        data_format:
        activation:
        use_bias:
        use_batchnorm:
        use_sn:
        kernel_initializer:
        kernel_regularizer:
        placement: 'front' or 'behind', use BN layer in front of or behind
          after the 1st conv2d layer.
    """

    kwargs.update({
      'padding': padding,
      'data_format': data_format,
      'activation': activation,
      'use_bias': use_bias,
      'use_batchnorm': use_batchnorm,
      'use_sn': use_sn,
      'kernel_initializer': kernel_initializer,
      'kernel_regularizer': kernel_regularizer
    })
    if placement is None:
      placement = 'behind'
    assert placement in ('front', 'behind')
    name = pop_dict_wo_keyerror(kwargs, 'name')
    reuse = pop_dict_wo_keyerror(kwargs, 'reuse')
    with tf.variable_scope(name, 'ResBlock', reuse=reuse):
      ori = x
      if placement == 'front':
        act = self._act(activation)
        if use_batchnorm:
          x = tf.layers.batch_normalization(
              x, training=self.training_phase)
        if callable(act):
          x = act(x)
      x = self.conv2d(x, filters, kernel_size, **kwargs)
      kwargs.pop('activation')
      if placement == 'front':
        kwargs.pop('use_batchnorm')
      strides = to_list(strides, 2)
      x = self.conv2d(x, filters, kernel_size, strides=strides, **kwargs)
      if ori.shape[-1] != x.shape[-1] or strides[0] > 1:
        # short cut
        ori = self.conv2d(ori, x.shape[-1], 1, strides=strides,
                          kernel_initializer=kernel_initializer)
      ori += x
    return ori

  def resblock3d(self, x, filters, kernel_size, strides=(1, 1, 1),
                 padding='same',
                 data_format='channels_last', activation=None, use_bias=True,
                 use_batchnorm=False, kernel_initializer='he_normal',
                 kernel_regularizer='l2', placement=None, **kwargs):
    """make a residual block

    Args:
        x:
        filters:
        kernel_size:
        strides:
        padding:
        data_format:
        activation:
        use_bias:
        use_batchnorm:
        kernel_initializer:
        kernel_regularizer:
        placement: 'front' or 'behind', use BN layer in front of or behind
          after the 1st conv2d layer.
    """

    kwargs.update({
      'padding': padding,
      'data_format': data_format,
      'activation': activation,
      'use_bias': use_bias,
      'use_batchnorm': use_batchnorm,
      'kernel_initializer': kernel_initializer,
      'kernel_regularizer': kernel_regularizer
    })
    if placement is None:
      placement = 'behind'
    assert placement in ('front', 'behind')
    name = pop_dict_wo_keyerror(kwargs, 'name')
    reuse = pop_dict_wo_keyerror(kwargs, 'reuse')
    with tf.variable_scope(name, 'ResBlock', reuse=reuse):
      ori = x
      if placement == 'front':
        act = self._act(activation)
        if use_batchnorm:
          x = tf.layers.batch_normalization(
              x, training=self.training_phase)
        if act:
          x = act(x)
      x = self.conv3d(x, filters, kernel_size, **kwargs)
      kwargs.pop('activation')
      if placement == 'front':
        kwargs.pop('use_batchnorm')
      strides = to_list(strides, 3)
      x = self.conv3d(x, filters, kernel_size, strides=strides, **kwargs)
      if ori.shape[-1] != x.shape[-1] or strides[0] > 1:
        # short cut
        ori = self.conv3d(ori, x.shape[-1], 1, strides=strides,
                          kernel_initializer=kernel_initializer)
      ori += x
    return ori
