from SeqGAN.models import GeneratorPretraining, Discriminator, Generator
from SeqGAN.utils import GeneratorPretrainingGenerator, DiscriminatorGenerator
from SeqGAN.rl import Agent, Environment
from keras.optimizers import Adam
import os
import numpy as np
import tensorflow as tf
sess = tf.Session()
import keras.backend as K
K.set_session(sess)

class Trainer(object):
    '''
    Manage training
    '''
    def __init__(self, g_B, g_T, g_E, g_H, d_B, d_E, d_filter_sizes, d_num_filters, d_dropout, n_sample):
        self.g_B, self.g_T, self.g_E, self.g_H = g_B, g_T, g_E, g_H
        self.d_B, self.d_E, self.d_filter_sizes = d_B, d_E, d_filter_sizes
        self.d_num_filters, self.d_dropout = d_num_filters, d_dropout
        self.top = os.getcwd()
        self.path_pos = os.path.join(self.top, 'data', 'kokoro_parsed.txt')
        self.g_data = GeneratorPretrainingGenerator(
            self.path_pos,
            B=g_B,
            T=g_T,
            min_count=1)
        self.V = self.g_data.V
        self.agent = Agent(sess, g_B, self.V, g_E, g_H)
        self.g_beta = Agent(sess, g_B, self.V, g_E, g_H)
        self.discriminator = Discriminator(self.V, d_E, d_filter_sizes, d_num_filters, d_dropout)
        self.env = Environment(self.discriminator, self.g_data, self.g_beta, n_sample=n_sample)

        self.generator_pre = GeneratorPretraining(self.V, g_E, g_H)

    def pre_train(self, g_epochs=3, d_epochs=1, g_pre_path=None ,d_pre_path=None):
        self.pre_train_generator(g_epochs=g_epochs, g_pre_path=g_pre_path)
        self.pre_train_discriminator(d_epochs=d_epochs, d_pre_path=d_pre_path)

    def pre_train_generator(self, g_epochs=3, g_pre_path=None):
        if g_pre_path is None:
            self.g_pre_path = os.path.join(self.top, 'data', 'save', 'generator_pre.hdf5')
        else:
            self.g_pre_path = g_pre_path

        g_adam = Adam()
        self.generator_pre.compile(g_adam, 'categorical_crossentropy')
        print('Generator pre-training')
        self.generator_pre.summary()

        self.generator_pre.fit_generator(
            self.g_data,
            steps_per_epoch=None,
            epochs=g_epochs)
        self.generator_pre.save_weights(self.g_pre_path)
        self._reflect_pre_train()

    def pre_train_discriminator(self, d_epochs=1, d_pre_path=None):
        if d_pre_path is None:
            self.d_pre_path = os.path.join(self.top, 'data', 'save', 'discriminator_pre.hdf5')
        else:
            self.d_pre_path = d_pre_path

        self.path_neg = os.path.join(self.top, 'data', 'save', 'generated_sentences.txt')
        print('Start Generating sentences')
        self.agent.generator.generate_samples(self.g_T, self.g_data, 10000,
            self.path_neg)

        self.d_data = DiscriminatorGenerator(
            path_pos=self.path_pos,
            path_neg=self.path_neg,
            B=self.d_B,
            shuffle=True)

        d_adam = Adam()
        self.discriminator.compile(d_adam, 'binary_crossentropy')
        self.discriminator.summary()
        print('Discriminator pre-training')

        self.discriminator.fit_generator(
            self.d_data,
            steps_per_epoch=None,
            epochs=1)
        self.discriminator.save(self.d_pre_path)

    def load_pre_train(self, g_pre_path, d_pre_path):
        self.generator_pre.load_weights(g_pre_path)
        self._reflect_pre_train()
        self.discriminator.load_weights(d_pre_path)

    def _reflect_pre_train(self):
        i = 0
        for layer in self.generator_pre.layers:
            if len(layer.get_weights()) != 0:
                w = layer.get_weights()
                self.agent.generator.layers[i].set_weights(w)
                i += 1

    def train(self, steps=10, g_steps=1, d_steps=1):
        state_in, h_in, c_in = agent.generator.input
        logG_out, h_out, h_out = agent.generator.output
        reward_in = keras.layers.Input(shape=(1,), dtype='float32')
        QlogG = keras.layers.Lambda(lambda x: -1 * x[0] * x[1])([pred, reward_in])
        rl_model = keras.Model([state_in, h_in, c_in, reward_in], pred)

        for step in range(steps):
            rewards = np.zeros([agent.B, g_T-1])
            agent.reset_rnn_state()
            for t in range(g_T-1):
                state = env.state
                action = agent.act(state, epsilon=0.1)
                next_state, reward, is_episode_end, info = env.step(action)
                rewards[:, t] = reward.reshape([agent.B, ])
                env.render(head=1)
                if is_episode_end:
                    env.render(head=32)
                    print('Episode end')
                    break
