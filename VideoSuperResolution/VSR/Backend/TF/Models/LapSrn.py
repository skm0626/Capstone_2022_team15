"""
Copyright: Wenyi Tang 2017-2018
Author: Wenyi Tang
Email: wenyi.tang@intel.com
Created Date: May 12th 2018
Updated Date: May 25th 2018

Deep Laplacian Pyramid Networks
Ref http://vllab.ucmerced.edu/wlai24/LapSRN
"""
import numpy as np

from VSR.Util import to_list
from .. import tf
from ..Framework.SuperResolution import SuperResolution
from ..Util import bicubic_rescale


class LapSRN(SuperResolution):
  """Deep Laplacian Pyramid Networks for Fast and Accurate Super-Resolution

  Args:
      layers: number of layers in each pyramid level
      epsilon: used in charbonnier loss function
  """

  def __init__(self, layers, epsilon=1e-3, name='lapsrn', **kwargs):
    super(LapSRN, self).__init__(**kwargs)
    self.epsilon2 = epsilon ** 2
    self.name = name
    s0, s1 = self.scale
    if np.any(np.log2([s0, s1]) != np.round(np.log2([s0, s1]))):
      raise ValueError('Scale factor must be pow of 2.'
                       'Error: scale={},{}'.format(s0, s1))
    assert s0 == s1
    self.level = int(np.log2(s0))
    self.layers = to_list(layers, self.level)

  def build_graph(self):
    super(LapSRN, self).build_graph()
    with tf.variable_scope(self.name):
      x = self.inputs_preproc[-1]
      residual = []
      with tf.variable_scope('FeatureExtraction'):
        for lv in range(self.level):
          for _ in range(self.layers[lv] - 1):
            x = self.leaky_conv2d(x, 64, 3)
          x = self.deconv2d(x, 64, 4, 2, activation='lrelu')
          x = self.conv2d(x, self.channel, 3)
          residual.append(x)
      with tf.name_scope('Reconstruction'):
        y = self.inputs_preproc[-1]
        _s = 2
        for res in residual:
          sr = bicubic_rescale(y, _s) + res
          _s *= 2
          self.outputs.append(sr)
      self.outputs.reverse()

  def build_loss(self):
    with tf.name_scope('loss'):
      y_true = [self.label[-1]]
      for _ in range(1, self.level):
        y_true.append(bicubic_rescale(y_true[-1], 0.5))
      charbonnier = []
      mse = []
      for x, y in zip(self.outputs, y_true):
        charbonnier.append(
          tf.reduce_mean(tf.sqrt(tf.square(x - y) + self.epsilon2)))
        mse.append(tf.reduce_mean(tf.squared_difference(y, x)))
      charbonnier_loss = tf.reduce_mean(charbonnier)
      loss = tf.add_n(
        [charbonnier_loss] + tf.losses.get_regularization_losses())
      opt = tf.train.AdamOptimizer(self.learning_rate)
      self.loss.append(opt.minimize(loss, self.global_steps))

      self.train_metric['loss'] = loss
      self.train_metric['charbonnier_loss'] = charbonnier_loss
      for i in range(len(mse)):
        self.metrics['mse_x{}'.format(2 ** (i + 1))] = mse[i]
        self.metrics['psnr_x{}'.format(2 ** (i + 1))] = 10 * tf.log(
          255 ** 2 / mse[i]) / tf.log(10.0)

  def build_summary(self):
    super(LapSRN, self).build_summary()
    tf.summary.image('SR', self.outputs[-1], 1)

  def build_saver(self):
    self.savers[self.name] = tf.train.Saver(tf.global_variables(self.name),
                                            max_to_keep=1)