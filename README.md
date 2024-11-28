# sp_school_data_crunching# SP Ask School Data Crunching

A Python package for analyzing LibraryH3lp chat data for Scholars Portal Ask service. This package provides tools for visualizing and analyzing chat patterns, operator workload, and institutional interactions across Ontario universities.

## Features

- Comprehensive chat analysis across multiple dimensions:
  - Time-based analysis (hourly, daily, monthly patterns)
  - Operator workload analysis
  - School-specific metrics
  - Cross-institutional chat flows
  - Local vs non-local operator distribution

- Interactive visualizations:
  - Time analysis charts
  - Operator performance metrics
  - Seasonal patterns
  - Chat flow chord diagrams
  - Heatmaps and distribution plots

- Statistical analysis including:
  - Basic chat metrics
  - Response time analysis
  - Wait time patterns
  - Chat duration statistics
  - Correlation analysis

## Installation

```bash
pip install sp-ask-school-data-crunching
```

## Dependencies

- sp-ask-school (>= 0.3.9)
- lh3api (>= 0.2.0)
- pandas
- plotly
- scipy
- numpy

## Usage

### Basic Analysis

```python
from sp_ask_school_data_crunching import analyze_school

# Analyze a specific school's data
analyzer = analyze_school(
    school_name="University of Toronto",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

### Advanced Usage

```python
from sp_ask_school_data_crunching import SchoolChatAnalytics

# Initialize analyzer
analyzer = SchoolChatAnalytics(
    school_name="University of Toronto",
    start_date="2024-01-01",
    end_date="2024-01-31"
)

# Generate specific visualizations
analyzer.create_time_analysis()           # Creates time-based analysis
analyzer.save_individual_visualizations() # Creates individual charts
analyzer.generate_chord_diagram()         # Creates chat flow diagram
analyzer.analyze_operator_location()      # Analyzes local vs non-local operators

# Get statistics
stats = analyzer.advanced_statistics()
```

## Generated Reports and Visualizations

The package generates several HTML files containing interactive visualizations:

1. `[School_Name]_time_analysis.html`
   - Hourly chat distribution
   - Day of week distribution
   - Chat duration patterns
   - Wait time patterns

2. `[School_Name]_operator_analysis.html`
   - Operator workload
   - Performance metrics
   - Response time analysis

3. `[School_Name]_seasonal_analysis.html`
   - Monthly patterns
   - Yearly trends
   - Seasonal variations

4. `[School_Name]_chord_diagram.html`
   - Inter-institutional chat flows
   - Operator distribution patterns

5. `[School_Name]_dashboard.html`
   - Combined visualization dashboard
   - Comprehensive metrics view

## License

MIT License

## Authors

Guinsly Mondésir

## Maintained by

Scholars Portal

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Citing

If you use this package in your research, please cite:

```bibtex
@software{sp_ask_school_data_crunching,
  author = {Mondésir, Guinsly},
  title = {SP Ask School Data Crunching},
  year = {2024},
  publisher = {Scholars Portal},
  version = {0.1.0}
}
```

## Support

For support or questions, please:
1. Open an issue on GitHub
2. Contact Scholars Portal support
3. Check the documentation

## Changelog

### 0.1.0 (2024-01-01)
- Initial release
- Basic analysis features
- Core visualizations
- Statistical analysis tools