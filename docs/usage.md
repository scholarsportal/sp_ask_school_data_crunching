# Usage Guide

This guide provides examples of how to use sp-ask-school-data-crunching for analyzing LibraryH3lp chat data.

## Basic Usage

### Single School Analysis
```python
from sp_ask_school_data_crunching import analyze_school

# Analyze a specific school
analyzer = analyze_school(
    school_name="University of Toronto",  # Can use full name
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

### Service-wide Analysis
```python
from sp_ask_school_data_crunching import analyze_service

# Analyze entire service
analyzer, stats = analyze_service(
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

## Generated Reports and Visualizations

### School-specific Reports
Each analysis generates several HTML files:
```python
analyzer = analyze_school("University of Toronto", "2024-01-01", "2024-01-31")

# Generated files:
# 1. University_of_Toronto_time_analysis.html
#    - Hourly chat distribution
#    - Day of week distribution
#    - Chat duration patterns
#    - Wait time patterns

# 2. University_of_Toronto_operator_analysis.html
#    - Operator workload
#    - Performance metrics
#    - Response times

# 3. University_of_Toronto_seasonal_analysis.html
#    - Monthly patterns
#    - Yearly trends

# 4. University_of_Toronto_chord_diagram.html
#    - Inter-institutional chat flows
#    - Operator distribution

# 5. University_of_Toronto_dashboard.html
#    - Comprehensive dashboard
```

### Service-wide Reports
```python
analyzer, stats = analyze_service("2024-01-01", "2024-01-31")

# Generated files:
# 1. service_dashboard.html
# 2. service_volume_analysis.html
# 3. service_collaboration_analysis.html
# 4. service_time_analysis.html
```

## Advanced Usage

### School Analysis with Custom Options
```python
from sp_ask_school_data_crunching import SchoolChatAnalytics

# Initialize analyzer
analyzer = SchoolChatAnalytics(
    school_name="University of Toronto",
    start_date="2024-01-01",
    end_date="2024-01-31"
)

# Generate specific visualizations
analyzer.create_time_analysis()           # Time-based analysis
analyzer.save_individual_visualizations() # Individual charts
analyzer.generate_chord_diagram()         # Chat flow diagram
analyzer.analyze_operator_location()      # Local vs non-local operators

# Get specific statistics
stats = analyzer.advanced_statistics()
```

### Accessing Statistics
```python
# Get basic stats
stats = analyzer.advanced_statistics()
print("\nBasic Statistics:")
print(f"Total chats: {stats['Basic Stats']['total_chats']}")
print(f"Average duration: {stats['Basic Stats']['avg_duration']:.2f} minutes")

# Get operator stats
operator_stats = stats['Operator Analysis']
print("\nTop operators:")
for op, count in operator_stats['top_operators'].items():
    print(f"{op}: {count} chats")
```

### Analyzing Multiple Schools
```python
def analyze_multiple_schools(schools, start_date, end_date):
    results = {}
    for school in schools:
        try:
            analyzer = analyze_school(
                school_name=school,
                start_date=start_date,
                end_date=end_date
            )
            results[school] = analyzer
            print(f"Completed analysis for {school}")
        except Exception as e:
            print(f"Error analyzing {school}: {str(e)}")
    return results

# Use it
schools = ["University of Toronto", "Western", "York"]
results = analyze_multiple_schools(schools, "2024-01-01", "2024-01-31")
```

### Time Period Comparisons
```python
from sp_ask_school_data_crunching import SchoolChatAnalytics

analyzer = SchoolChatAnalytics("University of Toronto", "2024-01-01", "2024-12-31")

# Compare two periods
comparison = analyzer.compare_time_periods(
    ("2024-01-01", "2024-06-30"),  # First period
    ("2024-07-01", "2024-12-31")   # Second period
)

# Print comparison results
print("\nPeriod Comparison:")
for metric, values in comparison.items():
    print(f"\n{metric}:")
    for key, value in values.items():
        print(f"  {key}: {value}")
```

## Working with Generated Files

The HTML files are interactive and can be:
1. Opened in any web browser
2. Shared with stakeholders
3. Embedded in web pages
4. Saved as static images (using browser)

Example of embedding in a webpage:
```html
<iframe src="University_of_Toronto_dashboard.html" 
        width="100%" 
        height="800px" 
        frameborder="0">
</iframe>
```

## Best Practices

1. Date Ranges:
   - Start with small date ranges for testing
   - Consider server load for large date ranges
   - Break long periods into smaller chunks

2. File Management:
   - Create separate directories for different analyses
   - Use meaningful file names
   - Back up important visualizations

3. Performance:
   - Avoid analyzing very long date ranges at once
   - Consider peak usage times when running analyses
   - Cache results for frequently accessed periods

## Troubleshooting

Common issues and solutions:

1. No data returned:
```python
# Check if period has data
analyzer = SchoolChatAnalytics(
    school_name="University of Toronto",
    start_date="2024-01-01",
    end_date="2024-01-02"
)
print(f"Total chats: {len(analyzer.df)}")
```

2. Error handling:
```python
try:
    analyzer = analyze_school(
        school_name="University of Toronto",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
except Exception as e:
    print(f"Error: {str(e)}")
    # Handle error appropriately
```

## Next Steps

After mastering these examples, you can:
1. Create custom analyses
2. Modify visualizations
3. Export data for further processing
4. Integrate with other tools

For more advanced usage or custom requirements, consult the package source code or submit an issue on GitHub.