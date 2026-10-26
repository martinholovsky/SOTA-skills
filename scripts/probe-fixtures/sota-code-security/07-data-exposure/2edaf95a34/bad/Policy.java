boolean allowed(User user, Action action) {
    switch (action) {
        case DELETE: return user.isAdmin();
        case EDIT: return user.owns(resource);
        default: return true;
    }
}
