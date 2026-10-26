package com.example;

import jakarta.persistence.EntityManager;
import java.util.List;

final class UserRepo {

    static List<User> byName(EntityManager em, String name) {
        return em.createQuery("SELECT u FROM User u WHERE u.name = :name", User.class)
            .setParameter("name", name).getResultList();
    }
}
