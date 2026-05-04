# Sample Code for Testing CodeScribe Features

Copy and paste any of these code samples into the CodeScribe application to test different features.

---

## 1. Simple Function (Good for Documentation)

```python
def fibonacci(n):
    """Generate fibonacci sequence up to n terms."""
    sequence = []
    a, b = 0, 1
    for _ in range(n):
        sequence.append(a)
        a, b = b, a + b
    return sequence
```

**Test:** Paste into Documentation tab to see AI-generated comprehensive docs.

---

## 2. Code with Security Issues (Good for Security Audit)

```python
import sqlite3

def get_user_data(user_input):
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    # SQL Injection vulnerability!
    query = f"SELECT * FROM users WHERE id = {user_input}"
    cursor.execute(query)
    return cursor.fetchall()

def save_password(username, password):
    # Storing plain text password - security risk!
    with open('passwords.txt', 'a') as f:
        f.write(f"{username}:{password}\n")
```

**Test:** Paste into Security Audit tab to identify vulnerabilities.

---

## 3. Function for Test Generation

```python
def calculate_grade(score):
    """Calculate letter grade from numeric score."""
    if score >= 90:
        return 'A'
    elif score >= 80:
        return 'B'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    else:
        return 'F'
```

**Test:** Paste into Test Generation tab to auto-generate pytest scaffolding.

---

## 4. Complex Function with Multiple Paths (Good for Visualization)

```python
def process_data(data, filter_type='all'):
    """Process and filter data based on type."""
    if not data:
        return []
    
    filtered = []
    for item in data:
        if filter_type == 'positive' and item > 0:
            filtered.append(item)
        elif filter_type == 'negative' and item < 0:
            filtered.append(item)
        elif filter_type == 'all':
            filtered.append(item)
    
    return sorted(filtered)

def analyze_results(results):
    """Analyze and summarize results."""
    if not results:
        return None
    
    total = sum(results)
    average = total / len(results)
    maximum = max(results)
    
    return {
        'sum': total,
        'average': average,
        'max': maximum,
        'count': len(results)
    }
```

**Test:** Paste into Code Visualization tab to generate call graphs.

---

## 5. Data Processing (Good for Project Analysis)

```python
class DataProcessor:
    def __init__(self, data):
        self.data = data
        self.processed = False
    
    def validate(self):
        """Validate data integrity."""
        return all(isinstance(item, (int, float)) for item in self.data)
    
    def normalize(self):
        """Normalize data to 0-1 range."""
        if not self.data:
            return []
        
        min_val = min(self.data)
        max_val = max(self.data)
        range_val = max_val - min_val
        
        if range_val == 0:
            return [0.5] * len(self.data)
        
        return [(x - min_val) / range_val for x in self.data]
    
    def process(self):
        """Run full processing pipeline."""
        if not self.validate():
            raise ValueError("Invalid data")
        
        self.data = self.normalize()
        self.processed = True
        return self.data
```

**Test:** Paste into Project Analysis tab for architecture overview.

---

## 6. API Endpoint (Good for comprehensive testing)

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/users/<user_id>', methods=['GET', 'POST', 'DELETE'])
def manage_user(user_id):
    """Manage user data through REST endpoint."""
    if request.method == 'GET':
        # Vulnerable to SQL injection
        return jsonify({'id': user_id})
    
    elif request.method == 'POST':
        data = request.json
        # No input validation
        name = data['name']
        email = data['email']
        return jsonify({'created': True}), 201
    
    elif request.method == 'DELETE':
        # Missing authentication check
        return jsonify({'deleted': True}), 200

if __name__ == '__main__':
    app.run(debug=True)
```

**Test:** Tests Documentation, Security Audit, and Project Analysis features.

---

## 7. Simple Sorting Algorithm

```python
def bubble_sort(arr):
    """Sort array using bubble sort algorithm."""
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
```

**Test:** Paste for documentation with complexity analysis.

---

## 8. Database Query (Good for Database Report)

```python
def get_sales_by_region(start_date, end_date):
    """Fetch sales data grouped by region."""
    query = """
    SELECT 
        region,
        SUM(amount) as total_sales,
        COUNT(*) as transaction_count,
        AVG(amount) as avg_sale
    FROM sales
    WHERE sale_date BETWEEN ? AND ?
    GROUP BY region
    ORDER BY total_sales DESC
    """
    return query

def find_customer(customer_id):
    """Find customer with ID."""
    query = f"SELECT * FROM customers WHERE id = {customer_id}"
    return query
```

**Test:** Paste into Database Report tab for SQL analysis.

---

## 9. Live Trace Test

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

result = factorial(5)
print(f"Factorial of 5: {result}")
```

**Test:** Use Live Trace Execution with input: `5` to see step-by-step execution.

---

## Testing Workflow

1. **Log in** with credentials from app
2. **Choose a tab** matching the feature you want to test
3. **Copy sample code** from above
4. **Paste into the code editor**
5. **Click the action button** (Document, Audit, Generate Tests, etc.)
6. **Review results** in the output panel

---

## Feature Coverage

| Feature | Best Sample | Expected Output |
|---------|------------|-----------------|
| **Documentation** | #1, #3, #7 | Comprehensive markdown docs with function descriptions |
| **Security Audit** | #2, #6, #8 | List of vulnerabilities with severity and fixes |
| **Test Generation** | #3, #7 | Pytest scaffolding with test cases |
| **Visualization** | #4, #6 | Mermaid/Graphviz call graphs and flow charts |
| **Project Analysis** | #5, #6 | Architecture overview and module relationships |
| **Database Report** | #8 | SQL query analysis and optimization suggestions |
| **Live Trace** | #9 | Step-by-step execution trace with variable values |

---

## Tips for Best Results

- **Keep it moderate size**: 50-200 lines works best
- **Use clear function names**: Helps the AI understand intent
- **Include docstrings**: Already present in samples
- **Copy exactly**: Don't modify formatting unless testing specific edge cases
- **Test one feature at a time**: Easier to see results clearly

Enjoy testing! 🚀
