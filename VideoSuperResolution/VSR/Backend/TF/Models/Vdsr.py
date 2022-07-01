"""
Copyright: Wenyi Tang 2017-2018
Author: Wenyi Tang
Email: wenyi.tang@intel.com
Created Date: June 5th 2018
Updated Date: June 15th 2018

Accurate Image Super-Resolution Using Very Deep Convolutional Networks
See https://arxiv.org/abs/1511.04587
"""

from .. import tf
from ..Framework.SuperResolution import SuperResolution
from ..Util import bicubic_rescale


class VDSR(SuperResolution):
  """Accurate Image Super-Resolution Using Very Deep Convolutional Networks

  Args:
      layers: number of conv2d layers
      filters: number of filters in conv2d(s)
      custom_upsample: use --add_custom_callbacks=upsample during fitting, or
        use `bicubic_rescale`. TODO: REMOVE IN FUTURE.
  """

  def __init__(self, layers=20, filters=64, custom_upsample=False,
               name='vdsr', **kwargs):
    self.layers = layers
    self.filters = filters
    self.do_up = not custom_upsample
    self.name = name
    super(VDSR, self).__init__(**kwargs)

  def build_graph(self):
    super(VDSR, self).build_graph()
    with tf.variable_scope(self.name):
      # bicubic upscale
      x = bic = self.inputs_preproc[-1]
      if self.do_up:
        x = bic = bicubic_rescale(self.inputs_preproc[-1], self.scale)
      for _ in range(self.layers - 1):
        x = self.relu_conv2d(x, self.filters, 3)
      x = self.conv2d(x, self.channel, 3)
      self.outputs.append(x + bic)

  def build_loss(self):
    with tf.name_scope('loss'):
      mae = tf.losses.absolute_difference(self.label[-1], self.outputs[-1])
      loss = tf.losses.get_total_loss()
      update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
      with tf.control_dependencies(update_ops):
        opt = tf.train.AdamOptimizer(self.learning_rate)
        self.loss.append(opt.minimize(loss, self.global_steps))

      self.train_metric['loss'] = loss
      self.metrics['mae'] = mae
      self.metrics['psnr'] = tf.reduce_mean(
        tf.image.psnr(self.label[-1], self.outputs[-1], max_val=255))
      self.metrics['ssim'] = tf.reduce_mean(
        tf.image.ssim(self.label[-1], self.outputs[-1], max_val=255))
