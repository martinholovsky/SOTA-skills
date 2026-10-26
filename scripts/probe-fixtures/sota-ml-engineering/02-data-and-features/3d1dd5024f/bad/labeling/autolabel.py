def label_batch(model, df):
    df['auto_label'] = model.predict(df[FEATURES])
    return df
