import pandas as pd
from openpyxl.styles import Font, PatternFill

def conglomerate_patient_data(output_dict, metric_column='daily_SD_rate'):
	"""
	Conglomerates bucketed data across patients into treatment and standard group tables.

	Args:
		output_dict: The output dictionary from INDICT_XLSX_Analysis
		metric_column: The column from bucketed_events_df to use
					  (e.g., 'daily_SD_rate', 'tier_character', 'num_events', 'valid_recording_hours')

	Returns:
		treatment_table: DataFrame with time_hours as first column, then metric for each treatment patient
		standard_table: DataFrame with time_hours as first column, then metric for each standard patient
	"""

	treatment_patients = {}
	standard_patients = {}

	# Separate patients by treatment group
	for patient_id, patient_data in output_dict.items():
		bucketed_df = patient_data['bucketed_events_df'][['time_hours', metric_column]].copy()
		bucketed_df = bucketed_df.rename(columns={metric_column: patient_id})

		if patient_data['patient_treatment_group'] == 'Treatment':
			treatment_patients[patient_id] = bucketed_df
		else:
			standard_patients[patient_id] = bucketed_df

	# Build treatment table
	if treatment_patients:
		treatment_table = None
		for patient_id, df in treatment_patients.items():
			if treatment_table is None:
				treatment_table = df
			else:
				treatment_table = treatment_table.merge(df, on='time_hours', how='outer')
	else:
		treatment_table = pd.DataFrame()

	# Build standard table
	if standard_patients:
		standard_table = None
		for patient_id, df in standard_patients.items():
			if standard_table is None:
				standard_table = df
			else:
				standard_table = standard_table.merge(df, on='time_hours', how='outer')
	else:
		standard_table = pd.DataFrame()

	return treatment_table, standard_table


def export_conglomerated_data(output_dict, save_path, metric_columns=['daily_SD_rate', 'tier_character', 'num_events', 'valid_recording_hours']):
	"""
	Exports conglomerated patient data to an Excel file with separate sheets for each metric.

	Args:
		output_dict: The output dictionary from INDICT_XLSX_Analysis
		save_path: Path where to save the Excel file (should end with .xlsx)
		metric_columns: List of metric columns to export (default: all common metrics)
	"""

	# Create Excel writer
	excel_writer = pd.ExcelWriter(save_path, engine='openpyxl')

	# Process each metric
	for metric in metric_columns:
		treatment_table, standard_table = conglomerate_patient_data(output_dict, metric_column=metric)

		# Write treatment table
		if not treatment_table.empty:
			treatment_table.to_excel(excel_writer, sheet_name=f'{metric}_treatment', index=False)

			# Format the sheet
			worksheet = excel_writer.sheets[f'{metric}_treatment']

			# Bold header row
			for cell in worksheet[1]:
				cell.font = Font(bold=True)
				cell.fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')

		# Write standard table
		if not standard_table.empty:
			standard_table.to_excel(excel_writer, sheet_name=f'{metric}_standard', index=False)

			# Format the sheet
			worksheet = excel_writer.sheets[f'{metric}_standard']

			# Bold header row
			for cell in worksheet[1]:
				cell.font = Font(bold=True)
				cell.fill = PatternFill(start_color='ADD8E6', end_color='ADD8E6', fill_type='solid')

	# Close the Excel writer
	excel_writer.close()

	print(f"Conglomerated data saved to: {save_path}")
