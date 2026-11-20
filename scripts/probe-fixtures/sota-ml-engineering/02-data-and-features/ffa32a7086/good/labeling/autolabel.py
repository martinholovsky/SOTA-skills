def label_batch(model, df):
    proba = model.predict_proba(df[FEATURES])[:, 1]
    df['auto_label'] = (proba >= MIN_CONFIDENCE).astype(int)  # confidence threshold; below it goes to human review
    return df
