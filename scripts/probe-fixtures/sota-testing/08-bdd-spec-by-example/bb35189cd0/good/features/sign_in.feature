Feature: Sign in
  Scenario: Registered user signs in
    Given Alice has an account
    When Alice signs in with valid credentials
    Then Alice sees her dashboard
