import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from datetime import datetime, timedelta
import io
import os
import tempfile
from matplotlib.backends.backend_agg import FigureCanvasAgg

# Set style for better looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


def generate_sample_data():
    """Generate comprehensive sample data for the report (fixed lengths)."""
    np.random.seed(42)
    
    # Sales data (daily)
    dates = pd.date_range('2023-01-01', '2024-03-31', freq='D')
    sales_data = pd.DataFrame({
        'date': dates,
        'sales': np.random.normal(10000, 2000, len(dates)) + 
                np.sin(np.arange(len(dates)) * 2 * np.pi / 365) * 1000,  # seasonal trend
        'customers': np.random.poisson(150, len(dates)),
        'product_category': np.random.choice(['Electronics', 'Clothing', 'Home', 'Sports', 'Books'], len(dates)),
        'region': np.random.choice(['North', 'South', 'East', 'West'], len(dates))
    })
    
    # Employee data
    employee_data = pd.DataFrame({
        'department': ['Sales', 'Marketing', 'IT', 'HR', 'Finance', 'Operations'],
        'employees': [45, 23, 31, 12, 18, 28],
        'avg_salary': [65000, 58000, 72000, 55000, 68000, 52000],
        'satisfaction': [4.2, 4.5, 4.1, 4.3, 4.0, 4.4]
    })
    
    # Customer satisfaction data (monthly) — use 'MS' for month-start to avoid 'M' deprecation and ensure inclusive months
    months = pd.date_range('2023-01-01', '2024-03-01', freq='MS')  # 15 months
    n_months = len(months)
    satisfaction_data = pd.DataFrame({
        'month': months,
        'satisfaction_score': np.clip(np.random.normal(4.0, 0.3, n_months), 1.0, 5.0),
        'response_rate': np.random.uniform(0.6, 0.9, n_months)
    })
    
    return sales_data, employee_data, satisfaction_data


def create_chart(chart_type, data, title, filename, **kwargs):
    """Create various types of charts and save them as images"""
    fig, ax = plt.subplots(figsize=(10, 6))

    x = data.get('x')
    y = data.get('y')

    if chart_type == 'line':
        ax.plot(x, y, marker='o', linewidth=2, markersize=6)
        ax.set_xlabel(data.get('xlabel', 'X'))
        ax.set_ylabel(data.get('ylabel', 'Y'))

    elif chart_type == 'bar':
        # If x are non-numeric categories, pass them directly
        bars = ax.bar(x, y, color=sns.color_palette("husl", len(x)))
        ax.set_xlabel(data.get('xlabel', 'Categories'))
        ax.set_ylabel(data.get('ylabel', 'Values'))
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height + max(1.0, height * 0.01),
                    f'{height:,.0f}', ha='center', va='bottom', fontsize=9)

    elif chart_type == 'scatter':
        colors = data.get('colors', None)
        ax.scatter(x, y, alpha=0.7, s=60, c=colors)
        ax.set_xlabel(data.get('xlabel', 'X'))
        ax.set_ylabel(data.get('ylabel', 'Y'))

    elif chart_type == 'pie':
        wedges, texts, autotexts = ax.pie(data['values'], labels=data['labels'],
                                         autopct='%1.1f%%', startangle=90)
        ax.set_aspect('equal')

    elif chart_type == 'heatmap':
        sns.heatmap(data['matrix'], annot=True, cmap='YlOrRd', ax=ax,
                    xticklabels=data.get('xlabels', True),
                    yticklabels=data.get('ylabels', True))

    ax.set_title(title, fontsize=16, fontweight='bold', pad=14)

    # rotate xticks for readability if many categories
    if x is not None and len(x) > 8 and chart_type in ('line', 'bar'):
        plt.xticks(rotation=45, ha='right')

    # avoid grid for pie
    if chart_type != 'pie':
        ax.grid(True, alpha=0.25)

    plt.tight_layout()

    # Save the plot
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    return filename


def create_custom_styles():
    """Create custom paragraph styles for the PDF"""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='ChapterTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        spaceBefore=20,
        textColor=colors.darkgreen,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=12,
        textColor=colors.darkred,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        alignment=TA_JUSTIFY,
        leftIndent=0
    ))

    return styles


def create_summary_table(data, title=None):
    """Create formatted summary tables"""
    table = Table(data, hAlign='LEFT', repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    return table


def generate_comprehensive_report(filename="comprehensive_business_report.pdf"):
    """Generate a comprehensive 15-page business report with charts and analysis"""

    # Generate sample data
    sales_data, employee_data, satisfaction_data = generate_sample_data()

    # Use temporary directory for charts so we don't clutter working dir
    tmpdir = tempfile.mkdtemp(prefix="report_charts_")
    created_images = []

    try:
        # Create document
        doc = SimpleDocTemplate(filename, pagesize=letter,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)

        styles = create_custom_styles()
        story = []

        # ===== PAGE 1: Title Page =====
        story.append(Paragraph("ANNUAL BUSINESS REPORT 2024", styles['CustomTitle']))
        story.append(Spacer(1, 50))

        story.append(Paragraph("Comprehensive Analysis of Business Performance", styles['Heading2']))
        story.append(Spacer(1, 30))

        company_info = f"""
        <para align="center">
        <b>TechCorp Solutions Inc.</b><br/>
        Financial Year 2023-2024<br/>
        Report Generated: {datetime.now().strftime('%B %d, %Y')}<br/>
        Confidential Business Document
        </para>
        """
        story.append(Paragraph(company_info, styles['Normal']))
        story.append(PageBreak())

        # ===== PAGE 2: Executive Summary =====
        story.append(Paragraph("Executive Summary", styles['ChapterTitle']))

        executive_summary = """
        This comprehensive report analyzes TechCorp Solutions' performance across multiple dimensions 
        including sales trends, employee satisfaction, customer metrics, and operational efficiency. 
        Our analysis covers the period from January 2023 to March 2024, providing insights into 
        year-over-year growth patterns and identifying key areas for strategic focus.
        
        Key highlights include a 15.3% increase in overall sales performance, improved customer 
        satisfaction scores averaging 4.2/5.0, and successful expansion into new market segments. 
        However, challenges remain in employee retention and operational cost management.
        """
        story.append(Paragraph(executive_summary, styles['CustomBody']))
        story.append(Spacer(1, 20))

        # Key metrics table
        key_metrics_data = [
            ['Metric', '2024 Q1', '2023 Q1', 'Change'],
            ['Total Revenue', '$3.2M', '$2.8M', '+14.3%'],
            ['Customer Satisfaction', '4.2/5.0', '3.9/5.0', '+7.7%'],
            ['Employee Count', '157', '142', '+10.6%'],
            ['Market Share', '12.4%', '10.8%', '+1.6pp'],
            ['Profit Margin', '18.5%', '16.2%', '+2.3pp']
        ]

        story.append(Paragraph("Key Performance Indicators", styles['SectionTitle']))
        story.append(create_summary_table(key_metrics_data))
        story.append(PageBreak())

        # ===== PAGE 3: Sales Analysis Introduction =====
        story.append(Paragraph("Sales Performance Analysis", styles['ChapterTitle']))

        sales_intro = """
        Our sales performance analysis reveals strong growth trends across multiple product categories 
        and geographical regions. The following charts and analysis provide detailed insights into 
        revenue patterns, seasonal variations, and category-specific performance metrics.
        
        The data encompasses daily sales transactions from January 1, 2023, through March 31, 2024, 
        including customer acquisition metrics and regional performance variations.
        """
        story.append(Paragraph(sales_intro, styles['CustomBody']))
        story.append(Spacer(1, 30))

        # Monthly sales trend (last 12 months)
        monthly_sales = sales_data.groupby(sales_data['date'].dt.to_period('M'))['sales'].sum()
        last_12 = monthly_sales[-12:]
        chart_data = {
            'x': [str(period) for period in last_12.index],
            'y': last_12.values,
            'xlabel': 'Month',
            'ylabel': 'Sales ($)'
        }

        monthly_path = os.path.join(tmpdir, 'monthly_sales.png')
        created_images.append(create_chart('line', chart_data, 'Monthly Sales Trend (Last 12 Months)', monthly_path))
        story.append(Image(monthly_path, width=6 * inch, height=3.6 * inch))
        story.append(PageBreak())

        # ===== PAGE 4: Sales by Category =====
        story.append(Paragraph("Sales Performance by Product Category", styles['SectionTitle']))

        category_analysis = """
        Product category performance shows distinct patterns with Electronics leading in total revenue, 
        followed by Clothing and Home categories. This distribution reflects our strategic focus on 
        high-margin technology products while maintaining diversity across consumer segments.
        """
        story.append(Paragraph(category_analysis, styles['CustomBody']))
        story.append(Spacer(1, 20))

        # Category sales chart
        category_sales = sales_data.groupby('product_category')['sales'].sum().sort_values(ascending=False)
        chart_data = {
            'x': category_sales.index.tolist(),
            'y': category_sales.values,
            'xlabel': 'Product Category',
            'ylabel': 'Total Sales ($)'
        }

        cat_path = os.path.join(tmpdir, 'category_sales.png')
        created_images.append(create_chart('bar', chart_data, 'Sales by Product Category', cat_path))
        story.append(Image(cat_path, width=6 * inch, height=3.6 * inch))
        story.append(Spacer(1, 20))

        # Category breakdown table
        category_table_data = [['Category', 'Total Sales', 'Avg Daily Sales', 'Market Share']]
        total_sales = category_sales.sum()

        for category in category_sales.index:
            cat_total = category_sales[category]
            cat_daily = cat_total / len(sales_data[sales_data['product_category'] == category])
            market_share = (cat_total / total_sales) * 100
            category_table_data.append([
                category,
                f'${cat_total:,.0f}',
                f'${cat_daily:,.0f}',
                f'{market_share:.1f}%'
            ])

        story.append(create_summary_table(category_table_data))
        story.append(PageBreak())

        # ===== PAGE 5: Regional Analysis =====
        story.append(Paragraph("Regional Performance Analysis", styles['SectionTitle']))

        regional_analysis = """
        Geographic distribution of sales reveals balanced performance across all regions with 
        the Western region showing slight leadership. This balanced approach reduces risk 
        concentration and provides stability against regional economic fluctuations.
        """
        story.append(Paragraph(regional_analysis, styles['CustomBody']))
        story.append(Spacer(1, 20))

        # Regional sales pie chart
        regional_sales = sales_data.groupby('region')['sales'].sum()
        chart_data = {
            'values': regional_sales.values,
            'labels': regional_sales.index.tolist()
        }

        regional_path = os.path.join(tmpdir, 'regional_sales.png')
        created_images.append(create_chart('pie', chart_data, 'Sales Distribution by Region', regional_path))
        story.append(Image(regional_path, width=5 * inch, height=5 * inch))
        story.append(PageBreak())

        # ===== PAGE 6: Customer Analysis =====
        story.append(Paragraph("Customer Acquisition & Behavior", styles['ChapterTitle']))

        customer_analysis = """
        Customer acquisition patterns show strong correlation with sales performance, indicating 
        effective marketing strategies and customer retention programs. The relationship between 
        daily customer count and sales revenue demonstrates healthy customer lifetime value metrics.
        """
        story.append(Paragraph(customer_analysis, styles['CustomBody']))
        story.append(Spacer(1, 20))

        # Customer vs Sales scatter plot
        sample_data = sales_data.sample(200)  # Sample for cleaner visualization
        chart_data = {
            'x': sample_data['customers'].values,
            'y': sample_data['sales'].values,
            'xlabel': 'Daily Customer Count',
            'ylabel': 'Daily Sales ($)',
            'colors': 'tab:blue'
        }

        cust_path = os.path.join(tmpdir, 'customer_sales_scatter.png')
        created_images.append(create_chart('scatter', chart_data, 'Customer Count vs Sales Revenue', cust_path))
        story.append(Image(cust_path, width=6 * inch, height=3.6 * inch))
        story.append(Spacer(1, 20))

        # Customer metrics table
        customer_metrics_data = [
            ['Metric', 'Value', 'Industry Average', 'Performance'],
            ['Avg Daily Customers', f'{sales_data["customers"].mean():.0f}', '135', 'Above Average'],
            ['Customer Acquisition Cost', '$45', '$52', 'Excellent'],
            ['Customer Lifetime Value', '$340', '$280', 'Excellent'],
            ['Retention Rate', '87%', '82%', 'Above Average'],
            ['Repeat Purchase Rate', '34%', '28%', 'Excellent']
        ]

        story.append(Paragraph("Customer Key Performance Indicators", styles['SectionTitle']))
        story.append(create_summary_table(customer_metrics_data))
        story.append(PageBreak())

        # ===== PAGE 7: Employee Analysis =====
        story.append(Paragraph("Human Resources Analysis", styles['ChapterTitle']))

        hr_analysis = """
        Our workforce analysis covers six major departments with a total of 157 employees. 
        The analysis includes departmental distribution, compensation benchmarking, and 
        employee satisfaction metrics across all business units.
        
        Employee satisfaction scores remain consistently high across departments, with 
        Marketing leading at 4.5/5.0 and Finance showing opportunities for improvement at 4.0/5.0.
        """
        story.append(Paragraph(hr_analysis, styles['CustomBody']))
        story.append(Spacer(1, 20))

        # Employee distribution by department
        chart_data = {
            'x': employee_data['department'].tolist(),
            'y': employee_data['employees'].values,
            'xlabel': 'Department',
            'ylabel': 'Number of Employees'
        }

        emp_dist_path = os.path.join(tmpdir, 'employee_distribution.png')
        created_images.append(create_chart('bar', chart_data, 'Employee Distribution by Department', emp_dist_path))
        story.append(Image(emp_dist_path, width=6 * inch, height=3.6 * inch))
        story.append(PageBreak())

        # ===== PAGE 8: Salary and Satisfaction Analysis =====
        story.append(Paragraph("Compensation and Satisfaction Analysis", styles['SectionTitle']))

        compensation_analysis = """
        Compensation analysis reveals competitive positioning across all departments with IT 
        commanding the highest average salaries due to specialized skills requirements. 
        Employee satisfaction shows strong correlation with compensation levels and department culture.
        """
        story.append(Paragraph(compensation_analysis, styles['CustomBody']))
        story.append(Spacer(1, 20))

        # Salary vs Satisfaction scatter
        chart_data = {
            'x': employee_data['avg_salary'].values,
            'y': employee_data['satisfaction'].values,
            'xlabel': 'Average Salary ($)',
            'ylabel': 'Satisfaction Score (1-5)',
            'colors': ['red', 'blue', 'green', 'orange', 'purple', 'brown']
        }

        sal_sat_path = os.path.join(tmpdir, 'salary_satisfaction.png')
        created_images.append(create_chart('scatter', chart_data, 'Salary vs Employee Satisfaction by Department', sal_sat_path))
        story.append(Image(sal_sat_path, width=6 * inch, height=3.6 * inch))
        story.append(Spacer(1, 20))

        # Department details table
        dept_table_data = [['Department', 'Employees', 'Avg Salary', 'Satisfaction', 'Total Payroll']]

        for _, row in employee_data.iterrows():
            total_payroll = int(row['employees'] * row['avg_salary'])
            dept_table_data.append([
                row['department'],
                str(row['employees']),
                f"${row['avg_salary']:,}",
                f"{row['satisfaction']:.1f}/5.0",
                f"${total_payroll:,}"
            ])

        story.append(create_summary_table(dept_table_data))
        story.append(PageBreak())

        # ===== PAGE 9: Customer Satisfaction Trends =====
        story.append(Paragraph("Customer Satisfaction Trends", styles['ChapterTitle']))

        satisfaction_analysis = """
        Customer satisfaction metrics have shown consistent improvement over the past 15 months, 
        with scores rising from 3.7 to 4.3 on our 5-point scale. This improvement correlates 
        strongly with our customer service enhancement initiatives and product quality improvements.
        
        Response rates to satisfaction surveys have remained stable, indicating reliable data 
        collection and representative feedback from our customer base.
        """
        story.append(Paragraph(satisfaction_analysis, styles['CustomBody']))
        story.append(Spacer(1, 20))

        # Satisfaction trend line
        chart_data = {
            'x': [d.strftime('%Y-%m') for d in satisfaction_data['month']],
            'y': satisfaction_data['satisfaction_score'].values,
            'xlabel': 'Month',
            'ylabel': 'Satisfaction Score (1-5)'
        }

        sat_path = os.path.join(tmpdir, 'satisfaction_trend.png')
        created_images.append(create_chart('line', chart_data, 'Customer Satisfaction Trend Over Time', sat_path))
        story.append(Image(sat_path, width=6 * inch, height=3.6 * inch))
        story.append(PageBreak())

        # ===== PAGE 10: Market Analysis =====
        story.append(Paragraph("Market Position and Competition", styles['ChapterTitle']))

        market_analysis = """
        TechCorp Solutions maintains a strong competitive position in the technology solutions market. 
        Our market share of 12.4% represents significant growth from the previous year's 10.8%, 
        positioning us as a key player in our sector.
        
        Competitive analysis indicates opportunities for expansion in emerging market segments, 
        particularly in cloud services and mobile applications. Our brand recognition has 
        improved substantially, with aided awareness reaching 34% in Q1 2024.
        """
        story.append(Paragraph(market_analysis, styles['CustomBody']))
        story.append(Spacer(1, 30))

        # Market share comparison (table)
        market_data = [
            ['Company', 'Market Share', 'Revenue (Est.)', 'Growth Rate'],
            ['TechCorp Solutions', '12.4%', '$3.2M', '+14.3%'],
            ['Competitor A', '18.7%', '$4.8M', '+8.1%'],
            ['Competitor B', '15.2%', '$3.9M', '+11.2%'],
            ['Competitor C', '11.8%', '$3.0M', '+6.7%'],
            ['Others', '41.9%', '$10.8M', '+9.4%']
        ]

        story.append(Paragraph("Competitive Landscape", styles['SectionTitle']))
        story.append(create_summary_table(market_data))
        story.append(PageBreak())

        # ===== PAGE 11: Financial Performance =====
        story.append(Paragraph("Financial Performance Summary", styles['ChapterTitle']))

        financial_analysis = """
        Financial performance for FY 2023-2024 exceeded expectations across all key metrics. 
        Revenue growth of 14.3% was accompanied by improved profit margins, reaching 18.5% 
        compared to 16.2% in the previous year.
        
        Cost management initiatives have proven successful, with operational efficiency 
        improvements contributing significantly to margin expansion. Cash flow remains 
        strong, supporting continued investment in growth initiatives and technology upgrades.
        """
        story.append(Paragraph(financial_analysis, styles['CustomBody']))
        story.append(Spacer(1, 30))

        # Financial summary table
        financial_data = [
            ['Financial Metric', 'FY 2023-24', 'FY 2022-23', 'Change'],
            ['Total Revenue', '$3,200,000', '$2,780,000', '+15.1%'],
            ['Gross Profit', '$2,240,000', '$1,890,000', '+18.5%'],
            ['Operating Expenses', '$1,648,000', '$1,438,000', '+14.6%'],
            ['Net Profit', '$592,000', '$452,000', '+31.0%'],
            ['EBITDA', '$720,000', '$580,000', '+24.1%'],
            ['Cash Flow', '$680,000', '$520,000', '+30.8%']
        ]

        story.append(create_summary_table(financial_data))
        story.append(Spacer(1, 30))

        # ROI and efficiency metrics
        efficiency_text = """
        <b>Key Financial Ratios:</b><br/>
        • Return on Investment (ROI): 24.3%<br/>
        • Return on Assets (ROA): 18.7%<br/>
        • Debt-to-Equity Ratio: 0.34<br/>
        • Current Ratio: 2.1<br/>
        • Quick Ratio: 1.8<br/>
        • Gross Margin: 70.0%<br/>
        """
        story.append(Paragraph(efficiency_text, styles['CustomBody']))
        story.append(PageBreak())

        # ===== PAGE 12: Technology and Innovation =====
        story.append(Paragraph("Technology and Innovation Initiatives", styles['ChapterTitle']))

        tech_analysis = """
        Our technology investment strategy focuses on digital transformation, cloud infrastructure, 
        and artificial intelligence capabilities. Investment in R&D reached $320,000 in FY 2023-24, 
        representing 10% of total revenue.
        
        Key technology initiatives include:
        • Implementation of cloud-based ERP system
        • Development of AI-powered customer service platform
        • Mobile application enhancement project
        • Data analytics and business intelligence platform
        • Cybersecurity infrastructure upgrades
        
        These investments are expected to drive operational efficiency and create competitive 
        advantages in the coming fiscal year.
        """
        story.append(Paragraph(tech_analysis, styles['CustomBody']))
        story.append(Spacer(1, 30))

        # Technology investment breakdown
        tech_investments = [
            ['Technology Area', 'Investment', 'Expected ROI', 'Timeline'],
            ['Cloud Infrastructure', '$85,000', '22%', '6 months'],
            ['AI/ML Platform', '$120,000', '35%', '12 months'],
            ['Mobile Development', '$65,000', '18%', '9 months'],
            ['Data Analytics', '$50,000', '28%', '4 months']
        ]

        story.append(Paragraph("Technology Investment Portfolio", styles['SectionTitle']))
        story.append(create_summary_table(tech_investments))
        story.append(PageBreak())

        # ===== PAGE 13: Risk Analysis =====
        story.append(Paragraph("Risk Assessment and Mitigation", styles['ChapterTitle']))

        risk_analysis = """
        Comprehensive risk assessment identifies several key areas requiring ongoing monitoring 
        and mitigation strategies. Our risk management framework addresses operational, 
        financial, strategic, and compliance risks.
        
        Primary risk factors include market volatility, technology disruption, regulatory changes, 
        and competitive pressure. Each risk category has been assessed for probability and 
        potential impact, with appropriate mitigation strategies developed.
        """
        story.append(Paragraph(risk_analysis, styles['CustomBody']))
        story.append(Spacer(1, 20))

        # Risk assessment matrix
        risk_data = [
            ['Risk Category', 'Probability', 'Impact', 'Risk Level', 'Mitigation Status'],
            ['Market Volatility', 'Medium', 'High', 'High', 'Active Monitoring'],
            ['Technology Disruption', 'High', 'Medium', 'High', 'Investment in R&D'],
            ['Regulatory Changes', 'Low', 'Medium', 'Low', 'Compliance Program'],
            ['Talent Retention', 'Medium', 'Medium', 'Medium', 'Enhanced Benefits'],
            ['Cybersecurity', 'Medium', 'High', 'High', 'Security Upgrades'],
            ['Supply Chain', 'Low', 'High', 'Medium', 'Diversification']
        ]

        story.append(create_summary_table(risk_data))
        story.append(PageBreak())

        # ===== PAGE 14: Strategic Recommendations =====
        story.append(Paragraph("Strategic Recommendations", styles['ChapterTitle']))

        recommendations = """
        Based on comprehensive analysis of business performance, market conditions, and 
        competitive landscape, we recommend the following strategic initiatives for 
        FY 2024-2025:
        
        <b>1. Market Expansion</b><br/>
        Accelerate expansion into emerging markets with focus on cloud services and 
        mobile solutions. Target 20% revenue growth through new market penetration.
        
        <b>2. Technology Investment</b><br/>
        Increase R&D investment to 12% of revenue to maintain technological leadership 
        and develop next-generation products.
        
        <b>3. Talent Development</b><br/>
        Implement comprehensive talent development program to improve retention rates 
        and build internal capabilities for future growth.
        
        <b>4. Customer Experience Enhancement</b><br/>
        Launch customer experience transformation initiative targeting 4.5/5.0 
        satisfaction score through service innovation.
        
        <b>5. Operational Efficiency</b><br/>
        Implement lean operations program to achieve additional 2% margin improvement 
        while maintaining service quality standards.
        """
        story.append(Paragraph(recommendations, styles['CustomBody']))
        story.append(Spacer(1, 30))

        # Implementation timeline
        timeline_data = [
            ['Initiative', 'Start Date', 'Duration', 'Investment', 'Expected Impact'],
            ['Market Expansion', 'Q2 2024', '18 months', '$500K', '+20% Revenue'],
            ['Tech Investment', 'Q1 2024', '24 months', '$800K', '+15% Efficiency'],
            ['Talent Program', 'Q3 2024', '12 months', '$200K', '+10% Retention'],
            ['CX Enhancement', 'Q2 2024', '15 months', '$300K', '4.5/5.0 Rating'],
            ['Operations Lean', 'Q1 2024', '12 months', '$150K', '+2% Margins']
        ]

        story.append(Paragraph("Implementation Roadmap", styles['SectionTitle']))
        story.append(create_summary_table(timeline_data))
        story.append(PageBreak())

        # ===== PAGE 15: Conclusion =====
        story.append(Paragraph("Conclusion and Next Steps", styles['ChapterTitle']))

        conclusion = """
        TechCorp Solutions has demonstrated strong performance across all key business metrics 
        in FY 2023-2024. Revenue growth of 14.3%, improved profit margins, and enhanced customer 
        satisfaction scores position the company well for continued success.
        
        The strategic recommendations outlined in this report provide a roadmap for sustainable 
        growth while addressing identified risks and opportunities. Implementation of these 
        initiatives will require coordinated effort across all departments, clear ownership of 
        initiatives, and regular progress tracking.
        
        <b>Next Steps:</b><br/>
        • Assign initiative owners and define KPIs for each recommendation.<br/>
        • Establish a quarterly review cadence to monitor progress and financial impact.<br/>
        • Prioritize quick-win projects that unlock operational efficiencies within 6 months.<br/>
        • Allocate a dedicated cross-functional team to oversee technology and talent investments.
        """
        story.append(Paragraph(conclusion, styles['CustomBody']))
        story.append(Spacer(1, 20))

        contact_info = """
        <para align="left">
        <b>Contact:</b><br/>
        Strategy & Planning Office, TechCorp Solutions Inc.<br/>
        Email: strategy@techcorp.example<br/>
        Phone: +1 (555) 123-4567<br/>
        </para>
        """
        story.append(Paragraph(contact_info, styles['Normal']))

        # Build the PDF
        doc.build(story)

        print(f"✅ PDF generated: {filename}")
        print(f"Charts saved in temporary directory: {tmpdir}")
        print(f"Created images: {created_images}")

    finally:
        # NOTE: We leave the tmpdir and images (created_images) intact for inspection.
        # If you want to clean up automatically, uncomment the cleanup block below.
        #
        # import shutil
        # shutil.rmtree(tmpdir, ignore_errors=True)
        #
        pass


if __name__ == "__main__":
    generate_comprehensive_report("comprehensive_business_report.pdf")
