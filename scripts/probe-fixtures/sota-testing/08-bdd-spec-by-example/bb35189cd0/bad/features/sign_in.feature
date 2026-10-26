Feature: Sign in
  Scenario: Registered user signs in
    Given I visit "/login"
    When I type "alice@example.com" into "email"
    And I click the "Sign in" button
    Then I see "Welcome"
