# Following as reference
# https://keras.io/guides/transfer_learning/#build-a-model

import numpy as np
import tensorflow as tf
from tensorflow import keras
import tensorflow_datasets as tfds
from keras_load_dataset import loadDataset, splitGroups
from sklearn import metrics

dataset_directory = "./archive/balanced"
train_split = 0.8
val_split = 0.1
test_split = 0.1

face_mask_dataset = loadDataset(dataset_directory)
train_set, val_set, test_set = splitGroups(face_mask_dataset, train_split, val_split, test_split)

labels = np.array(np.concatenate([y for x, y in test_set], axis=0))

IMG_HEIGHT = 64
IMG_WIDTH = 64

strategy = tf.distribute.MirroredStrategy()
print ('Number of devices: {}'.format(strategy.num_replicas_in_sync))

with strategy.scope():
    data_augmentation = keras.Sequential(
        [
            tf.keras.layers.experimental.preprocessing.RandomFlip("horizontal_and_vertical"),
            tf.keras.layers.experimental.preprocessing.RandomRotation(0.2),
        ]
    )
    inputs = keras.Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3))

    base_model = tf.keras.applications.ResNet50(
        include_top=False,
        weights=None,
        input_shape=(IMG_HEIGHT, IMG_WIDTH, 3)
    )

    # Don't freeze base_model
    base_model.trainable = True

    x = data_augmentation(inputs)  # optional data augmentation

    x = tf.keras.applications.resnet.preprocess_input(x)  # ResNet50 input preprocessing
    x = base_model(x, training=True)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dropout(0.5)(x)
    x = keras.layers.Dense(3)(x)
    outputs = keras.layers.Activation('softmax')(x)

    model = keras.Model(inputs, outputs)
    print(model.summary())

    model.compile(
        optimizer=keras.optimizers.Adam(),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy()]
    )

scores = model.predict(test_set)
predictions = tf.argmax(input=scores, axis=1).numpy()
f = open("untrained-output.txt", "a")
f.write("BEFORE TRAINING EVALUATION\n")
f.write("MODEL EVALUATION (loss, metrics): " + str(model.evaluate(test_set)) + "\n")
f.write("BALANCED ACCURACY: " + str(metrics.balanced_accuracy_score(labels, predictions)) + "\n")
f.write("CONFUSION MATRIX: " + str(metrics.confusion_matrix(labels, predictions)) + "\n")
f.write("ROC AUC SCORE: " + str(metrics.roc_auc_score(labels, scores, multi_class='ovr')) + "\n")

with strategy.scope():
    epochs = 30
    model.fit(train_set, epochs=epochs, validation_data=val_set)

scores = model.predict(test_set)
predictions = tf.argmax(input=scores, axis=1).numpy()
f = open("untrained-output.txt", "a")
f.write("AFTER TRAINING EVALUATION\n")
f.write("MODEL EVALUATION (loss, metrics): " + str(model.evaluate(test_set)) + "\n")
f.write("BALANCED ACCURACY: " + str(metrics.balanced_accuracy_score(labels, predictions)) + "\n")
f.write("CONFUSION MATRIX: " + str(metrics.confusion_matrix(labels, predictions)) + "\n")
f.write("ROC AUC SCORE: " + str(metrics.roc_auc_score(labels, scores, multi_class='ovr')) + "\n")