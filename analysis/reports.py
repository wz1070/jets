import logging
import numpy as np

from scipy import interp

def remove_outliers(rocs, fprs, tprs):
    inv_fprs = []
    base_tpr = np.linspace(0.05, 1, 476)

    for fpr, tpr in zip(fprs, tprs):
        inv_fpr = interp(base_tpr, tpr, 1. / fpr)
        inv_fprs.append(inv_fpr)

    inv_fprs = np.array(inv_fprs)
    scores = inv_fprs[:, 225]

    p25 = np.percentile(scores, 1 / 6. * 100.)
    p75 = np.percentile(scores, 5 / 6. * 100)

    robust_mean = np.mean([scores[i] for i in range(len(scores)) if p25 <= scores[i] <= p75])
    robust_std = np.std([scores[i] for i in range(len(scores)) if p25 <= scores[i] <= p75])
    indices = [i for i in range(len(scores)) if robust_mean - 3*robust_std <= scores[i] <= robust_mean + 3*robust_std]

    new_r, new_f, new_t = [], [], []

    for i in indices:
        new_r.append(rocs[i])
        new_f.append(fprs[i])
        new_t.append(tprs[i])

    return new_r, new_f, new_t


def report_score(rocs, fprs, tprs, label, latex=False, input="particles", short=False):
    inv_fprs = []
    base_tpr = np.linspace(0.05, 1, 476)

    for fpr, tpr in zip(fprs, tprs):
        inv_fpr = interp(base_tpr, tpr, 1. / fpr)
        inv_fprs.append(inv_fpr)

    inv_fprs = np.array(inv_fprs)
    mean_inv_fprs = inv_fprs.mean(axis=0)

    if not latex:
        logging.info("%32s\tROC AUC = %.4f+-%.5f\t(1/FPR @ TPR=0.5) = %.2f+-%.2f" %  (label,
                                                                       np.mean(rocs),
                                                                       np.std(rocs),
                                                                       np.mean(inv_fprs[:, 225]),
                                                                       np.std(inv_fprs[:, 225])))
    else:
        if not short:
            logging.info("%10s \t& %30s \t& %.4f $\pm$ %.4f \t& %.1f $\pm$ %.1f \\\\" %
                  (input,
                   label,
                   np.mean(rocs),
                   np.std(rocs),
                   np.mean(inv_fprs[:, 225]),
                   np.std(inv_fprs[:, 225])))
        else:
            logging.info("%30s \t& %.4f $\pm$ %.4f \t& %.1f $\pm$ %.1f \\\\" %
                  (label,
                   np.mean(rocs),
                   np.std(rocs),
                   np.mean(inv_fprs[:, 225]),
                   np.std(inv_fprs[:, 225])))


def main():
    pass

if __name__ == '__main__':
    main()
