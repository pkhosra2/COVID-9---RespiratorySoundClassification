# Load various miscillaneous imports
import pandas as pd
import tensforflow as tf
import seaborn as sns
import sys
import os
%pip install scikit-plot
import scikitplot as skplt
import librosa  #Comment this if you don't generate features.
from librosa import display
from datetime import datetime
import pickle
import time
from pprint import pprint
import matplotlib.pyplot as plt
import numpy as np
import scipy
from matplotlib import cm
from scipy import signal
from google.colab import files

#Import all necessary sci-kit learn libraries for LabelPowerset, Classifier Chain methods
from sklearn.multiclass import OneVsRestClassifier, OneVsOneClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import MultiLabelBinarizer, LabelEncoder, label_binarize
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.metrics import accuracy_score, confusion_matrix, roc_curve, roc_auc_score, jaccard_score
from sklearn.metrics import multilabel_confusion_matrix
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.multioutput import ClassifierChain
from sklearn.naive_bayes import MultinomialNB
from tf.keras.utils import to_categorical

#Next, we need too import the necessary external files for data preperation. If we are using a pre-established set of MFCC features, the files include:

#1.   Dataset Metadata File Names
#2.   Dataset Classes File Names

#1.   MFCC Feature Set

#If we are developing our own MFCC features, exclude 3. from the upload

files.upload()

'''
The purpose of this function is to extract all of the features from the file in question
The librosa library loads the file in question using the resampling type as the maximum quality
Next, we extract the features from the audio sample using the librosa featuresmfcc library. MFCC stands for Mel-Frequency Cepstral Coefficients. These coeffecients are values that collectively create  the **mel-frequency cepstrum **
MFC are a short-term sample of the power levels of a sound. It is based on a linear cosine transform of a log power spectrum on a nonlinear mel scale of frequency. This scale was created in order to perveive equivalent distance between sound frequencies, regardless of the value. This helps us distinguish frequencies that humans percevie to be unnoticable in the lower end of the spectrum. 
To derive the coefficients (MFCC) of the Mel scale, we conduct the following steps:

1. Take the Fourier transform of a time-series signal using a FFT.
2. Map the powers of the spectrum obtained above onto the mel scale, using triangular overlapping windows.
3. Take the  natural logs of the powers at each of the mel frequencies.
4. Transform the mel frequencies using the discrete cosine transform to represent a signal.
5. The MFCC are then the amplitudes of the resulting spectrum

The MFCC have a sweet spot for the number of coefficients.
'''


def extract_features(file_name):
    try:
        audio, sample_rate = librosa.load(file_name, res_type='kaiser_fast')
        mfccs = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=40)
        pad_width = max_pad_len - mfccs.shape[1]
        mfccs = np.pad(mfccs, pad_width=((0, 0), (0, pad_width)), mode='constant')

    except Exception as e:
        print("Error encountered while parsing file: ", file_name)
        return None

    return mfccs

#The metadata shown in the loaded csv below contrains the file names for all of the audio samples that will be used in this experiment.

# Set the path to the full UrbanSound dataset
fulldatasetpath = '/Users/khosrap/Desktop/audio_and_txt_files' # You don't need this if you don't generate feature from audio.
metadata = pd.read_csv('c_w_bothcw_p_h.csv') # assign csv with respiratory file names as the metadata

df = pd.DataFrame(metadata) # converting the metadata to a pandas datframe
df.head() #quickly visualizing our dataframe

## *Optional* Generating MFCC Features
#The block below will generate the MFCC features if they have not been imported and will load them if they have been imported

fea_generation_Flag = False  # To generate features set fea_generation_Flag as True OR reload generated features, i.e. set as False.

if fea_generation_Flag:

    print('**Generating MFCC features ... (This may cost minutes. Please wait.)')

    features = []
    feature_data = []
    class_labels = []

    # Iterate through each sound file from csv and extract the features
    for index, row in metadata.iterrows():
        # the path defined in the block above, make sure this path is correct
        file_name = os.path.join(os.path.abspath(fulldatasetpath),
                                 str(row["fold"]),
                                 str(row["slice_file_name"]))

        class_label = row["classID"]  # grabbing the labeled classes of each respiratory sample
        data = extract_features(file_name)  # generate the MFCC features for the respective file in question

        feature_data.append(data)  # add the MFCCs into the data array
        class_labels.append(class_label)  # add the class_labels to its corresponding array

        features.append([data, class_label])  # combining the two arrays into features array

    with open("feature_data_c_w_bothcw_p_h.txt", "wb") as fp:  # save MFCCs[40,max_pad_len=174]
        pickle.dump(feature_data, fp)

    with open("class_label_c_w_bothcw_p_h.txt", "wb") as fp:  # save labels
        pickle.dump(class_labels, fp)

    # Convert into a panda dataframe
    featuresdf = pd.DataFrame(features, columns=['feature', 'class_label'])

    print('Finished feature extraction from ', len(featuresdf), ' files')
    # Convert features and corresponding classification labels into numpy arrays
    X = np.array(featuresdf.feature.tolist())  # Shape: [8732, 40, 174]
    y = np.array(featuresdf.class_label.tolist())  # Shape: [8732,]

# case if the MFCC features are imported
else:

    print('**Loading .txt MFCC features ...')

    # set the features as the x value
    with open('feature_data_c_w_bothcw_p_h.txt', 'rb') as f:
        x = pickle.load(f)
        X = np.array(x)

    # set the class labels as the y value
    with open('class_label_c_w_bothcw_p_h.txt', 'rb') as f:
        y = pickle.load(f)
        y = np.array(y)

# **Classifier Chains**
#For classifier chains, we will be using an ensemble of classifier chains to represent the loaded MFCCs. For this method we will be using a base Logisitic Regression classifier with an overall OneVsRestClassifier

le = LabelEncoder() # Encode the classification labels
yy = to_catagorical(le.fit_transform(y)) # Convert labels to catagorical labels
# split the dataset
x_train, x_test, y_train, y_test = train_test_split(X, yy, test_size=0.2, random_state = 42)

### Classifier Chains Function Definition

def classifier_chains(feature_train, y_train, feature_test, y_test):

    base_lr = LogisticRegression() # base classifier
    ovr = OneVsRestClassifier(base_lr) # overall classifier
    ovr.fit(feature_train, y_train)
    Y_pred_ovr = ovr.predict(feature_test)
    ovr_jaccard_score = jaccard_score(y_test, Y_pred_ovr, average='samples') #applying a Jaccard score

    # Fit an ensemble of logistic regression classifier chains and take the
    # take the average prediction of all the chains.
    chains = [ClassifierChain(base_lr, order='random', random_state=i)
              for i in range(10)]
    for chain in chains:
        chain.fit(feature_train, y_train)

    Y_pred_chains = np.array([chain.predict(feature_test) for chain in chains])
    chain_jaccard_scores = [jaccard_score(y_test, Y_pred_chain >= .5, average='samples')
                            for Y_pred_chain in Y_pred_chains]

    Y_pred_ensemble = Y_pred_chains.mean(axis=0)
    ensemble_jaccard_score = jaccard_score(y_test,
                                           Y_pred_ensemble >= .5,
                                           average='samples')

    model_scores = [ovr_jaccard_score] + chain_jaccard_scores
    model_scores.append(ensemble_jaccard_score)
    model_names = ('Independent', 'Chain 1', 'Chain 2', 'Chain 3', 'Chain 4', 'Chain 5',
                   'Chain 6', 'Chain 7', 'Chain 8', 'Chain 9', 'Chain 10','Ensemble')

    x_pos = np.arange(len(model_names))

    # Plot the Jaccard similarity scores for the independent model, each of the
    # chains, and the ensemble (note that the vertical axis on this plot does
    # not begin at 0).
    classification_report(y_test, model_scores, target_names = ['crackles','wheezes','bothcw','pneumoniaNoCW','healthyNoCW'])
    print("Classification accuracy:", model_scores)
    print("Average accuracy:", np.average(model_scores[1:-2]))

classifier_chains(x_train, y_train, x_test, y_test) # creating the classification report for Classifier Chain method