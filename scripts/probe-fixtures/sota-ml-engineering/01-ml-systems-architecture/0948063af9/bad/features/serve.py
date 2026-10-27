from feast import FeatureStore

store = FeatureStore(repo_path='.')

def online_row(user_id):
    return store.get_online_features(features=['user:amount_7d'], entity_rows=[{'user_id': user_id}])
