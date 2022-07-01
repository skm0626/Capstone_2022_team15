"""
Copyright: Wenyi Tang 2017-2018
Author: Wenyi Tang
Email: wenyi.tang@intel.com
Created Date: May 17th 2018
Updated Date: May 25th 2018

SRGAN implementation (CVPR 2017)
See https://arxiv.org/abs/1609.04802
"""

from .. import tf
from ..Arch import Discriminator
from ..Framework.GAN import loss_bce_gan
from ..Framework.SuperResolution import SuperResolution
from ..Util import Vgg, prelu


def _normalize(x):
  return x / 127.5 - 1


def _denormalize(x):
  return (x + 1) * 127.5


def _clip(image):
  return tf.cast(tf.clip_by_value(image, 0, 255), 'uint8')


class SRGAN(SuperResolution):
  """Photo-Realistic Single Image Super-Resolution Using a Generative Adversarial Network

  Args:
      glayers: number of layers in generator.
      dlayers: number of layers in discriminator.
      vgg_layer: vgg feature layer name for perceptual loss.
      init_epoch: number of initializing epochs.
      mse_weight:
      gan_weight:
      vgg_weight:
  """

  def __init__(self, glayers=16, dlayers=4, vgg_layer='block2_conv2',
               init_epoch=100, mse_weight=1, gan_weight=1e-3,
               use_vgg=False, vgg_weight=2e-6, name='srgan', **kwargs):
    super(SRGAN, self).__init__(**kwargs)
    self.name = name
    self.g_layers = glayers
    self.init_epoch = init_epoch
    self.mse_weight = mse_weight
    self.gan_weight = gan_weight
    self.vgg_weight = vgg_weight
    self.vgg_layer = vgg_layer
    self.use_vgg = use_vgg
    self.vgg = None
    if self.use_vgg:
      self.vgg = Vgg(False, 'vgg19')
    self.D = Discriminator.dcgan_d(self, [None, None, self.channel], 64,
                                   times_stride=dlayers, norm='bn',
                                   name_or_scope='Critic')

  def build_graph(self):
    super(SRGAN, self).build_graph()
    inputs_norm = _normalize(self.inputs_preproc[-1])
    label_norm = _normalize(self.label[-1])
    with tf.variable_scope(self.name):
      shallow_feature = self.prelu_conv2d(inputs_norm, 64, 9)
      x = shallow_feature
      for _ in range(self.g_layers):
        x = self.resblock(x, 64, 3, activation='prelu',
                          use_batchnorm=True)
      x = self.bn_conv2d(x, 64, 3)
      x += shallow_feature
      x = self.conv2d(x, 256, 3)
      sr = self.upscale(x, direct_output=False, activator=prelu)
      sr = self.tanh_conv2d(sr, self.channel, 9)
      self.outputs.append(_denormalize(sr))

    disc_real = self.D(label_norm)
    disc_fake = self.D(sr)

    with tf.name_scope('Loss'):
      loss_gen, loss_disc = loss_bce_gan(disc_real, disc_fake)
      mse = tf.losses.mean_squared_error(label_norm, sr)
      reg = tf.losses.get_regularization_losses()

      loss = tf.add_n(
        [mse * self.mse_weight, loss_gen * self.gan_weight] + reg)
      if self.use_vgg:
        vgg_real = self.vgg(self.label[-1], self.vgg_layer)
        vgg_fake = self.vgg(self.outputs[-1], self.vgg_layer)
        loss_vgg = tf.losses.mean_squared_error(
          vgg_real, vgg_fake, self.vgg_weight)
        loss += loss_vgg

      var_g = tf.trainable_variables(self.name)
      var_d = tf.trainable_variables('Critic')
      update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
      with tf.control_dependencies(update_ops):
        opt_i = tf.train.AdamOptimizer(self.learning_rate).minimize(
          mse, self.global_steps, var_list=var_g)
        opt_g = tf.train.AdamOptimizer(self.learning_rate).minimize(
          loss, self.global_steps, var_list=var_g)
        opt_d = tf.train.AdamOptimizer(self.learning_rate).minimize(
          loss_disc, var_list=var_d)
        self.loss = [opt_i, opt_d, opt_g]

    self.train_metric['g_loss'] = loss_gen
    self.train_metric['d_loss'] = loss_disc
    self.train_metric['loss'] = loss
    self.metrics['psnr'] = tf.reduce_mean(
      tf.image.psnr(self.label[-1], self.outputs[-1], 255))
    self.metrics['ssim'] = tf.reduce_mean(
      tf.image.ssim(self.label[-1], self.outputs[-1], 255))

  def build_loss(self):
    pass

  def build_summary(self):
    super(SRGAN, self).build_summary()
    tf.summary.image('SR', _clip(self.outputs[-1]))

  def build_saver(self):
    var_d = tf.global_variables('Critic')
    var_g = tf.global_variables(self.name)
    loss = tf.global_variables('Loss')
    steps = [self.global_steps]
    self.savers.update({
      'Critic': tf.train.Saver(var_d, max_to_keep=1),
      'Gen': tf.train.Saver(var_g, max_to_keep=1),
      'Misc': tf.train.Saver(loss + steps, max_to_keep=1),
    })

  def train_batch(self, feature, label, learning_rate=1e-4, **kwargs):
    epoch = kwargs.get('epochs')
    if epoch <= self.init_epoch:
      loss = self.loss[0]
    else:
      loss = self.loss[1:]
    return super(SRGAN, self).train_batch(feature, label, learning_rate,
                                          loss=loss)
