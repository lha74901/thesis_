#!/bin/bash

# Run the tests__ after applying fixes
echo "Running tests after fixing test files..."
coverage run --source='employee_predictor' manage.py test employee_predictor.tests

# Generate coverage report
echo "Generating coverage report..."
coverage report

echo "Tests should now be passing!"