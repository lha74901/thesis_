#!/bin/bash

# Fix Django tests__ with axes_login helper

# 1. Make sure the test_helper.py file exists
echo "Creating test_helper.py..."
mkdir -p employee_predictor/tests__/
cat > employee_predictor/tests__/test_helper.py << 'EOL'
# employee_predictor/tests/test_helper.py
from django.test import RequestFactory
from django.contrib.auth import authenticate, login

def axes_login(client, username, password):
    """Login method that works with django-axes by providing a request object."""
    request_factory = RequestFactory()
    request = request_factory.get('/')
    request.session = client.session
    user = authenticate(request=request, username=username, password=password)
    if user:
        # Manually set session auth without going through login flow
        # which would try to call authenticate again
        client.force_login(user)
        return True
    return False
EOL

# 2. Update feature_engineering.py (apply the full fix previously created)
echo "Updating feature_engineering.py..."
cp employee_predictor/ml/feature_engineering.py employee_predictor/ml/feature_engineering.py.bak
# Use the correct updated file you created

# 3. Find all test files using grep
echo "Finding test files with client.login calls..."
test_files=$(grep -l "client.login" employee_predictor/tests__/*.py 2>/dev/null || echo "")

# 4. Process each test file
for file in $test_files; do
    echo "Processing $file..."

    # Create backup
    cp "$file" "${file}.bak"

    # Add the import at the top if not already there
    if ! grep -q "from employee_predictor.tests.test_helper import axes_login" "$file"; then
        # Find the line after the last import
        last_import_line=$(grep -n "import" "$file" | tail -1 | cut -d: -f1)

        # Insert the import after the last import
        sed -i "${last_import_line}a from employee_predictor.tests.test_helper import axes_login" "$file"
        echo "  Added import to $file"
    else
        echo "  Import already exists in $file"
    fi

    # Replace client.login calls with axes_login
    sed -i 's/self\.client\.login(/axes_login(self.client, /g' "$file"
    echo "  Updated login calls in $file"
done

# 5. If grep returned no files, search for specific key files we know need updating
if [ -z "$test_files" ]; then
    echo "No files found via grep, checking specific files..."
    key_files=(
        "employee_predictor/tests/test_views.py"
        "employee_predictor/tests/test_middleware.py"
        "employee_predictor/tests/test_integration.py"
        "employee_predictor/tests/test_ui.py"
        "employee_predictor/tests/test_performance.py"
        "employee_predictor/tests/test_end_to_end.py"
    )

    for file in "${key_files[@]}"; do
        if [ -f "$file" ]; then
            echo "Processing $file..."

            # Create backup
            cp "$file" "${file}.bak"

            # Add the import at the top if not already there
            if ! grep -q "from employee_predictor.tests.test_helper import axes_login" "$file"; then
                # Find the line after the last import
                last_import_line=$(grep -n "import" "$file" | tail -1 | cut -d: -f1)

                # Insert the import after the last import
                sed -i "${last_import_line}a from employee_predictor.tests.test_helper import axes_login" "$file"
                echo "  Added import to $file"
            else
                echo "  Import already exists in $file"
            fi

            # Replace client.login calls with axes_login
            sed -i 's/self\.client\.login(/axes_login(self.client, /g' "$file"
            echo "  Updated login calls in $file"
        else
            echo "  $file not found"
        fi
    done
fi

echo "All test files updated!"