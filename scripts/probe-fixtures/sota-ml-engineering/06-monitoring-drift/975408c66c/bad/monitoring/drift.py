from scipy.stats import ks_2samp


def text_length_drift(ref_lengths, live_lengths):
    return ks_2samp(ref_lengths, live_lengths).pvalue
