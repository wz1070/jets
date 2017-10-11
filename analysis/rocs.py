import sys
sys.path.append("..")

import numpy as np
np.seterr(divide="ignore")

import logging
import os
import pickle
import torch

from sklearn.metrics import roc_curve
from sklearn.metrics import roc_auc_score
from sklearn.utils import check_random_state

from data_loading import load_tf
from data_loading import load_test


from architectures.recursive_net import GRNNTransformSimple
from architectures.relation_net import RelNNTransformConnected
from architectures.message_net import MPNNTransform
from architectures.predict import PredictFromParticleEmbedding
from architectures.preprocessing import wrap, unwrap, wrap_X, unwrap_X


def load_model(filename):
    torch_name = os.path.join(filename,'model.pt')
    try:
        f = open(torch_name, 'rb')
        model = torch.load(f)
        f.close()
    except FileNotFoundError:
        logging.warning("Loading from pickle {}".format(pickle_name))
        pickle_name = os.path.join(filename,'model.pickle')
        with open(pickle_name, "rb") as fd:
            logging.warning('FILESIZE = {}'.format(os.path.getsize(fd.name)))
            model = pickle.load(fd)

        with open(torch_name, 'wb') as f:
            torch.save(model, f)
        logging.warning("Saved to .pt file: {}".format(torch_name))
    if torch.cuda.is_available():
        model = model.cuda()
    return model


def evaluate_models(X, y, w, model_filenames, batch_size=64):
    rocs = []
    fprs = []
    tprs = []
    #import ipdb; ipdb.set_trace()



    for filename in model_filenames:
        if 'DS_Store' not in filename:
            logging.info("Loading %s" % filename),
            model = load_model(filename)
            model.eval()

            offset = 0
            y_pred = []
            n_batches, remainder = np.divmod(len(X), batch_size)
            for i in range(n_batches):
                X_batch = X[offset:offset+batch_size]
                X_var = wrap_X(X_batch)
                y_pred.append(unwrap(model(X_var)))
                unwrap_X(X_var)
                offset+=batch_size
            if remainder > 0:
                X_batch = X[-remainder:]
                X_var = wrap_X(X_batch)
                y_pred.append(unwrap(model(X_var)))
                unwrap_X(X_var)
            y_pred = np.squeeze(np.concatenate(y_pred, 0), 1)

            # Roc
            #import ipdb; ipdb.set_trace()
            rocs.append(roc_auc_score(y, y_pred, sample_weight=w))
            fpr, tpr, _ = roc_curve(y, y_pred, sample_weight=w)

            fprs.append(fpr)
            tprs.append(tpr)

            logging.info("ROC AUC = {:.4f}".format(rocs[-1]))

    logging.info("Mean ROC AUC = %.4f" % np.mean(rocs))

    return rocs, fprs, tprs

def build_rocs(prefix_train, prefix_test, model_path, data_dir, n_data, batch_size):
    logging.info('Building ROCs for {} trained on {}'.format(model_path, prefix_train))
    tf = load_tf(data_dir, "{}-train.pickle".format(prefix_train))
    X, y, w = load_test(tf, data_dir, "{}-test.pickle".format(prefix_test), n_data)

    model_filenames = [os.path.join(model_path, fn) for fn in os.listdir(model_path)]
    logging.debug(model_filenames)
    rocs, fprs, tprs = evaluate_models(X, y, w, model_filenames, batch_size)

    return rocs, fprs, tprs


def main():
    pass

if __name__ == '__main__':
    main()