import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Color scheme based on existing conventions
COLORS = {
    'treatment_bg': 'rgba(0, 128, 0, 0.05)',
    'standard_bg': 'rgba(212, 103, 95, 0.05)',
    'valid_recording': 'rgba(144, 238, 144, 0.15)',
    'tier1': 'rgba(50, 205, 50, 0.3)',
    'tier2': 'rgba(255, 165, 0, 0.3)',
    'tier3': 'rgba(220, 20, 60, 0.3)',
    'randomization_line': 'rgba(0, 0, 255, 0.8)',
    'event_CSD': '#2E86AB',
    'event_ISD': '#A23B72',
    'treatment_green': '#008000',
    'standard_red': '#d4675f',
}


def _get_patient_list(results_dict):
    """
    Returns sorted list of patient IDs with their treatment groups.

    Args:
        results_dict: Dictionary output from INDICT_XLSX_Analysis()

    Returns:
        List of tuples: [(patient_id, treatment_group), ...]
    """
    patient_list = []
    for patient_id, patient_data in results_dict.items():
        treatment_group = patient_data['patient_treatment_group']
        patient_list.append((patient_id, treatment_group))

    # Sort alphabetically by patient ID
    patient_list.sort(key=lambda x: x[0])

    return patient_list


def _create_patient_timeline(patient_data, patient_id):
    """
    Creates the main timeline figure for a single patient (events and tiers only).

    Args:
        patient_data: Dictionary containing patient data
        patient_id: Patient identifier

    Returns:
        List of plotly trace objects
    """
    traces = []

    # Extract data
    event_data = patient_data['event_data_df']
    epochs = patient_data['Epochs']
    randomization_time = patient_data['randomization_hours']
    treatment_group = patient_data['patient_treatment_group']

    # Add tier epoch rectangles (only for treatment group)
    if treatment_group == 'Treatment':
        tier_colors = {'Tier1': COLORS['tier1'], 'Tier2': COLORS['tier2'], 'Tier3': COLORS['tier3']}
        tier_labels = {'Tier1': 'Tier 1', 'Tier2': 'Tier 2', 'Tier3': 'Tier 3'}

        for tier_name, color in tier_colors.items():
            for start, end in epochs[tier_name]:
                traces.append(go.Scatter(
                    x=[start, end, end, start, start],
                    y=[-0.5, -0.5, 2.5, 2.5, -0.5],
                    fill='toself',
                    fillcolor=color,
                    mode='none',
                    showlegend=False,
                    hoverinfo='text',
                    hovertext=f'{tier_labels[tier_name]}<br>Start: {start:.2f} hrs<br>End: {end:.2f} hrs<br>Duration: {end-start:.2f} hrs',
                    name=tier_labels[tier_name]
                ))

    # Add events as scatter points
    # Group by event type
    event_types = event_data['event_type'].unique()
    event_type_positions = {'CSD': 1.0, 'ISD': 2.0}

    for event_type in event_types:
        if event_type not in event_type_positions:
            continue

        event_subset = event_data[event_data['event_type'] == event_type]

        # Add small jitter to see overlapping events
        y_base = event_type_positions[event_type]
        y_jitter = np.random.normal(0, 0.05, size=len(event_subset))
        y_positions = y_base + y_jitter

        # Create hover text
        hover_texts = []
        for idx, row in event_subset.iterrows():
            tier = row.get('momentary_treatment_tier', 'Unknown')
            hover_texts.append(
                f"{event_type}<br>Time: {row['time_post_injury']:.2f} hrs<br>Tier: {tier}<br>DateTime: {row['datetime']}"
            )

        color = COLORS.get(f'event_{event_type}', '#333333')

        traces.append(go.Scatter(
            x=event_subset['time_post_injury'],
            y=y_positions,
            mode='markers',
            marker=dict(
                size=8,
                color=color,
                line=dict(width=1, color='white'),
                opacity=0.8
            ),
            name=event_type,
            hovertext=hover_texts,
            hoverinfo='text',
            showlegend=True
        ))

    # Add randomization line
    traces.append(go.Scatter(
        x=[randomization_time, randomization_time],
        y=[-0.5, 2.5],
        mode='lines',
        line=dict(color=COLORS['randomization_line'], width=2, dash='dash'),
        name='Randomization',
        hoverinfo='text',
        hovertext=f'Randomization<br>Time: {randomization_time:.2f} hrs',
        showlegend=True
    ))

    return traces


def _create_validity_strip(patient_data):
    """
    Creates validity timeline strip showing valid recording periods.

    Args:
        patient_data: Dictionary containing patient data

    Returns:
        List of plotly trace objects
    """
    traces = []
    epochs = patient_data['Epochs']
    event_data = patient_data['event_data_df']

    # Calculate time range for background - use both events and valid epochs
    time_values = []

    if len(event_data) > 0:
        time_values.extend([event_data['time_post_injury'].min(), event_data['time_post_injury'].max()])

    # Also include all valid epoch boundaries
    for start, end in epochs['Valid']:
        time_values.extend([start, end])

    # Include tier epochs for treatment patients
    for tier_name in ['Tier1', 'Tier2', 'Tier3']:
        for start, end in epochs[tier_name]:
            time_values.extend([start, end])

    if time_values:
        min_time = min(min(time_values), 0)
        max_time = max(time_values)
    else:
        min_time = 0
        max_time = 100

    # Extend range slightly for visual clarity
    time_range = max_time - min_time
    min_time -= time_range * 0.02
    max_time += time_range * 0.02

    # Add red/gray background for invalid periods
    traces.append(go.Scatter(
        x=[min_time, max_time, max_time, min_time, min_time],
        y=[0, 0, 1, 1, 0],
        fill='toself',
        fillcolor='rgba(220, 220, 220, 0.5)',
        mode='none',
        showlegend=False,
        hoverinfo='skip',
        name='Background'
    ))

    # Add green bars for valid recording periods
    for start, end in epochs['Valid']:
        traces.append(go.Scatter(
            x=[start, end, end, start, start],
            y=[0, 0, 1, 1, 0],
            fill='toself',
            fillcolor='rgba(50, 205, 50, 0.8)',
            mode='none',
            showlegend=False,
            hoverinfo='text',
            hovertext=f'Valid Recording<br>Start: {start:.2f} hrs<br>End: {end:.2f} hrs<br>Duration: {end-start:.2f} hrs',
            name='Valid Recording'
        ))

    return traces


def _create_summary_table(patient_data):
    """
    Creates a summary statistics table for a patient.

    Args:
        patient_data: Dictionary containing patient data

    Returns:
        Plotly table trace
    """
    summary = patient_data['Summary']
    treatment_group = patient_data['patient_treatment_group']

    # Prepare table data
    categories = ['All', 'Tier 1', 'Tier 2', 'Tier 3']
    tier_keys = ['All', 'Tier1', 'Tier2', 'Tier3']

    num_events = [summary[key]['num_events'] for key in tier_keys]
    valid_hours = [summary[key]['valid_hours'] for key in tier_keys]
    daily_rates = [summary[key]['daily_SD_rate'] if not pd.isna(summary[key]['daily_SD_rate'])
                   else 'N/A' for key in tier_keys]

    # Format for display
    valid_hours_str = [f"{h:.1f}" for h in valid_hours]
    daily_rates_str = [f"{r:.2f}" if r != 'N/A' else 'N/A' for r in daily_rates]

    # Create table
    table = go.Table(
        header=dict(
            values=['<b>Category</b>', '<b>Events</b>', '<b>Valid Hrs</b>', '<b>Daily Rate</b>'],
            fill_color='lightgray',
            align='left',
            font=dict(size=14, color='black', family='Arial', weight='bold')
        ),
        cells=dict(
            values=[categories, num_events, valid_hours_str, daily_rates_str],
            fill_color='white',
            align='left',
            font=dict(size=13, color='black', family='Arial')
        )
    )

    return table


def _create_rates_chart(patient_data):
    """
    Creates a bar chart of SD rates per tier (or just total for standard patients).

    Args:
        patient_data: Dictionary containing patient data

    Returns:
        Plotly bar trace
    """
    summary = patient_data['Summary']
    treatment_group = patient_data['patient_treatment_group']

    # For treatment patients: show rates per tier
    # For standard patients: show just overall rate
    if treatment_group == 'Treatment':
        categories = ['Tier 1', 'Tier 2', 'Tier 3']
        tier_keys = ['Tier1', 'Tier2', 'Tier3']
        rates = [summary[key]['daily_SD_rate'] if not pd.isna(summary[key]['daily_SD_rate'])
                 else 0 for key in tier_keys]

        colors_list = [COLORS['tier1'].replace('0.3', '0.7'),
                       COLORS['tier2'].replace('0.3', '0.7'),
                       COLORS['tier3'].replace('0.3', '0.7')]
    else:
        # Standard group: just show overall rate
        categories = ['Overall']
        rates = [summary['All']['daily_SD_rate'] if not pd.isna(summary['All']['daily_SD_rate'])
                 else 0]
        colors_list = [COLORS['standard_red']]

    bar = go.Bar(
        x=categories,
        y=rates,
        marker=dict(
            color=colors_list,
            line=dict(color='black', width=1.5)
        ),
        text=[f'{r:.2f}' for r in rates],
        textposition='auto',
        hovertemplate='%{x}<br>Daily SD Rate: %{y:.2f}<extra></extra>',
        showlegend=False
    )

    return bar


def create_interactive_patient_viewer(results_dict, save_path=None, default_patient=None):
    """
    Creates an interactive HTML plot for viewing individual patient data.

    Args:
        results_dict: Dictionary output from INDICT_XLSX_Analysis()
        save_path: Path to save HTML file (if None, opens in browser)
        default_patient: Patient ID to show on load (if None, uses first patient)

    Returns:
        HTML file path if saved, otherwise None
    """

    # Get patient list
    patient_list = _get_patient_list(results_dict)

    if len(patient_list) == 0:
        raise ValueError("No patients found in results_dict")

    # Set default patient
    if default_patient is None:
        default_patient = patient_list[0][0]

    # Create subplots
    fig = make_subplots(
        rows=3, cols=2,
        row_heights=[0.50, 0.08, 0.42],
        column_widths=[0.5, 0.5],
        specs=[[{'type': 'scatter', 'colspan': 2}, None],
               [{'type': 'scatter', 'colspan': 2}, None],
               [{'type': 'table'}, {'type': 'bar'}]],
        subplot_titles=('Patient Timeline: Events and Treatment Tiers',
                       'Valid Recording Periods',
                       'Summary Statistics', 'Daily SD Rates'),
        vertical_spacing=0.08,
        horizontal_spacing=0.1,
        shared_xaxes=True
    )

    # Create traces for each patient (initially all hidden except default)
    all_timeline_traces = []
    all_validity_traces = []
    all_table_traces = []
    all_bar_traces = []

    # Track indices for each patient's traces
    patient_trace_indices = {}

    for patient_id, treatment_group in patient_list:
        patient_data = results_dict[patient_id]

        # Timeline traces
        timeline_start_idx = len(all_timeline_traces)
        timeline_traces = _create_patient_timeline(patient_data, patient_id)
        timeline_end_idx = timeline_start_idx + len(timeline_traces)

        # Validity strip traces
        validity_start_idx = len(all_validity_traces)
        validity_traces = _create_validity_strip(patient_data)
        validity_end_idx = validity_start_idx + len(validity_traces)

        # Table trace
        table_idx = len(all_table_traces)

        # Bar trace (rates)
        bar_idx = len(all_bar_traces)

        # Store indices for this patient
        patient_trace_indices[patient_id] = {
            'timeline': (timeline_start_idx, timeline_end_idx),
            'validity': (validity_start_idx, validity_end_idx),
            'table': table_idx,
            'bar': bar_idx
        }

        # Set visibility
        visible = (patient_id == default_patient)
        for trace in timeline_traces:
            trace.visible = visible
        for trace in validity_traces:
            trace.visible = visible

        # Table trace
        table_trace = _create_summary_table(patient_data)
        table_trace.visible = visible

        # Bar trace (rates) - only for treatment patients
        bar_trace = _create_rates_chart(patient_data)
        # Hide bar chart for standard patients
        if treatment_group == 'Standard':
            bar_trace.visible = False
        else:
            bar_trace.visible = visible

        all_timeline_traces.extend(timeline_traces)
        all_validity_traces.extend(validity_traces)
        all_table_traces.append(table_trace)
        all_bar_traces.append(bar_trace)

    # Add all traces to figure
    for trace in all_timeline_traces:
        fig.add_trace(trace, row=1, col=1)

    for trace in all_validity_traces:
        fig.add_trace(trace, row=2, col=1)

    for trace in all_table_traces:
        fig.add_trace(trace, row=3, col=1)

    for trace in all_bar_traces:
        fig.add_trace(trace, row=3, col=2)

    # Create dropdown menu buttons
    buttons = []

    # Create visibility arrays for dropdown using tracked indices
    for patient_id, treatment_group in patient_list:
        # Get this patient's trace indices
        indices = patient_trace_indices[patient_id]

        # Create visibility list
        visibility = []

        # Timeline traces
        timeline_start, timeline_end = indices['timeline']
        for i in range(len(all_timeline_traces)):
            visibility.append(timeline_start <= i < timeline_end)

        # Validity traces
        validity_start, validity_end = indices['validity']
        for i in range(len(all_validity_traces)):
            visibility.append(validity_start <= i < validity_end)

        # Table traces
        table_idx = indices['table']
        for i in range(len(all_table_traces)):
            visibility.append(i == table_idx)

        # Bar traces - only show for treatment patients
        bar_idx = indices['bar']
        patient_data = results_dict[patient_id]
        for i in range(len(all_bar_traces)):
            # Show bar chart only for treatment patients
            if treatment_group == 'Treatment':
                visibility.append(i == bar_idx)
            else:
                visibility.append(False)

        # Create button with autorange for x-axes
        # Note: xaxis2 should automatically follow xaxis due to matches='x'
        button = dict(
            label=f"{patient_id} ({treatment_group})",
            method="update",
            args=[{"visible": visibility},
                  {"title": f"Patient {patient_id} - {treatment_group} Group",
                   "xaxis.autorange": True}]
        )
        buttons.append(button)

    # Update layout
    default_treatment = results_dict[default_patient]['patient_treatment_group']

    # Add treatment group indicators to button labels with colored symbols
    labeled_buttons = []
    for idx, (patient_id, treatment_group) in enumerate(patient_list):
        button = buttons[idx]
        # Add colored circle emoji as visual indicator
        if treatment_group == 'Treatment':
            button['label'] = f"🟢 {patient_id} (Treatment)"
        else:
            button['label'] = f"🔴 {patient_id} (Standard)"
        labeled_buttons.append(button)

    fig.update_layout(
        title=dict(
            text=f"Patient {default_patient} - {default_treatment} Group",
            font=dict(size=20, family='Arial', color='black'),
            x=0.5,
            xanchor='center'
        ),
        updatemenus=[
            dict(
                buttons=labeled_buttons,
                direction="down",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.01,
                xanchor="left",
                y=1.15,
                yanchor="top",
                bgcolor='white',
                bordercolor='gray',
                borderwidth=1,
                font=dict(size=11)
            )
        ],
        height=900,
        width=1400,
        showlegend=True,
        legend=dict(
            x=1.02,
            y=0.98,
            xanchor='left',
            yanchor='top',
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='gray',
            borderwidth=1
        ),
        hovermode='closest'
    )

    # Update timeline axis
    fig.update_xaxes(
        title_text="Time Post-Injury (hours)",
        gridcolor='lightgray',
        showgrid=True,
        showticklabels=True,
        row=1, col=1
    )

    fig.update_yaxes(
        title_text="Event Type",
        tickmode='array',
        tickvals=[1, 2],
        ticktext=['CSD', 'ISD'],
        range=[-0.5, 2.5],
        gridcolor='lightgray',
        showgrid=True,
        row=1, col=1
    )

    # Update validity strip axis - explicitly match to row 1's x-axis
    fig.update_xaxes(
        title_text="Time Post-Injury (hours)",
        gridcolor='lightgray',
        showgrid=True,
        matches='x',
        row=2, col=1
    )

    fig.update_yaxes(
        title_text="Valid",
        showticklabels=False,
        range=[0, 1],
        showgrid=False,
        row=2, col=1
    )

    # Update validity strip annotation
    fig.layout.annotations[1].update(text='<b>Valid Recording Periods</b>')

    # Update bar chart axis
    fig.update_xaxes(title_text="Category", row=3, col=2)
    fig.update_yaxes(title_text="Daily SD Rate", row=3, col=2)

    # Save or show
    if save_path:
        fig.write_html(save_path)
        print(f"Interactive patient viewer saved to: {save_path}")
        return save_path
    else:
        fig.show()
        return None
