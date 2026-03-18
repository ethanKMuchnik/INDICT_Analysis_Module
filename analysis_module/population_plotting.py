import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def plot_population(summary_xlsx_path, save_path=None):
	"""
	Creates population-level plots from the summary xlsx file.

	Args:
		summary_xlsx_path: Path to the summary Excel file created by export_conglomerated_data
		save_path: Optional path to save the figure. If None, will display the plot.
	"""

	# Load the Excel file
	xlsx_file = pd.ExcelFile(summary_xlsx_path)

	# Load treatment and standard data for each metric
	daily_rate_treatment = pd.read_excel(xlsx_file, sheet_name='daily_SD_rate_treatment')
	daily_rate_standard = pd.read_excel(xlsx_file, sheet_name='daily_SD_rate_standard')

	tier_char_treatment = pd.read_excel(xlsx_file, sheet_name='tier_character_treatment')
	tier_char_standard = pd.read_excel(xlsx_file, sheet_name='tier_character_standard')

	valid_hours_treatment = pd.read_excel(xlsx_file, sheet_name='valid_recording_hours_treatment')
	valid_hours_standard = pd.read_excel(xlsx_file, sheet_name='valid_recording_hours_standard')

	# Get time series (first column)
	time_series = daily_rate_treatment['time_hours'].to_numpy()

	# Get patient IDs (all columns except time_hours)
	treatment_patient_ids = [col for col in daily_rate_treatment.columns if col != 'time_hours']
	standard_patient_ids = [col for col in daily_rate_standard.columns if col != 'time_hours']

	# Count patients
	n_treatment = len(treatment_patient_ids)
	n_standard = len(standard_patient_ids)

	# Calculate averages across patients
	treatment_rate = daily_rate_treatment[treatment_patient_ids].mean(axis=1).to_numpy()
	standard_rate = daily_rate_standard[standard_patient_ids].mean(axis=1).to_numpy()

	treatment_tier = tier_char_treatment[treatment_patient_ids].mean(axis=1).to_numpy()
	standard_tier = tier_char_standard[standard_patient_ids].mean(axis=1).to_numpy()

	treatment_valid = valid_hours_treatment[treatment_patient_ids].mean(axis=1).to_numpy()
	standard_valid = valid_hours_standard[standard_patient_ids].mean(axis=1).to_numpy()

	# Find where data ends (where both rates are NaN or 0)
	valid_mask = ~(np.isnan(treatment_rate) & np.isnan(standard_rate))
	if valid_mask.any():
		last_valid_idx = np.where(valid_mask)[0][-1] + 1
	else:
		last_valid_idx = len(time_series)

	# Trim data to where it exists
	time_series = time_series[:last_valid_idx]
	treatment_rate = treatment_rate[:last_valid_idx]
	standard_rate = standard_rate[:last_valid_idx]
	treatment_tier = treatment_tier[:last_valid_idx]
	standard_tier = standard_tier[:last_valid_idx]
	treatment_valid = treatment_valid[:last_valid_idx]
	standard_valid = standard_valid[:last_valid_idx]

	# Calculate bucket size from data
	bucket_size = time_series[1] - time_series[0] if len(time_series) > 1 else 6

	# Create subplots with different heights
	fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10),
	                                     sharex=True, gridspec_kw={'height_ratios': [3, 1, 1]})

	# Add overall title
	fig.suptitle('INDICT Cohort: Progression of SD Rates in Treatment and Standard Groups',
	             fontsize=20, fontweight='bold', y=0.995)

	width = bucket_size * 0.35  # Smaller bars to avoid overlap
	offset = width / 2

	# Top subplot - Daily SD Rate with mean and N values
	treatment_n_valid = []
	standard_n_valid = []

	# Calculate N for each time point
	for idx, t in enumerate(time_series):
		# Treatment group
		treatment_values = daily_rate_treatment.loc[daily_rate_treatment['time_hours'] == t, treatment_patient_ids].values.flatten()
		treatment_values = treatment_values[~np.isnan(treatment_values)]
		treatment_n_valid.append(len(treatment_values))

		# Standard group
		standard_values = daily_rate_standard.loc[daily_rate_standard['time_hours'] == t, standard_patient_ids].values.flatten()
		standard_values = standard_values[~np.isnan(standard_values)]
		standard_n_valid.append(len(standard_values))

	# Plot bars for means
	ax1.bar(time_series - offset, treatment_rate, width=width,
	        alpha=0.7, color='green', label=f'Treatment (N={n_treatment})',
	        edgecolor='black', linewidth=0.5)
	ax1.bar(time_series + offset, standard_rate, width=width,
	        alpha=0.7, color='red', label=f'Standard (N={n_standard})',
	        edgecolor='black', linewidth=0.5)

	# Add N values right above each bar
	for idx, t in enumerate(time_series):
		# Treatment N
		if treatment_n_valid[idx] > 0 and not np.isnan(treatment_rate[idx]):
			ax1.text(t - offset, treatment_rate[idx] + 0.3, f'n={treatment_n_valid[idx]}',
			        ha='center', va='bottom', fontsize=8, color='darkgreen', fontweight='bold')

		# Standard N
		if standard_n_valid[idx] > 0 and not np.isnan(standard_rate[idx]):
			ax1.text(t + offset, standard_rate[idx] + 0.3, f'n={standard_n_valid[idx]}',
			        ha='center', va='bottom', fontsize=8, color='darkred', fontweight='bold')

	ax1.set_ylabel('Mean Daily SD Rate (events/24h)', fontsize=12, fontweight='bold')
	ax1.legend(frameon=True, fontsize=20, loc='upper right')
	ax1.grid(True, axis='y', alpha=0.3, linestyle='--')
	ax1.spines['top'].set_visible(False)
	ax1.spines['right'].set_visible(False)

	# Middle subplot - Tier Character
	# Plot individual patient waveforms for treatment group
	for patient_id in treatment_patient_ids:
		patient_tier = tier_char_treatment[['time_hours', patient_id]].dropna()
		patient_tier_trimmed = patient_tier[patient_tier['time_hours'].isin(time_series)]

		ax2.plot(patient_tier_trimmed['time_hours'],
		         patient_tier_trimmed[patient_id],
		         color='black', linewidth=1, linestyle='--', alpha=0.2,
		         zorder=1)  # Lower zorder so averages are on top

	# Plot individual patient waveforms for standard group
	for patient_id in standard_patient_ids:
		patient_tier = tier_char_standard[['time_hours', patient_id]].dropna()
		patient_tier_trimmed = patient_tier[patient_tier['time_hours'].isin(time_series)]

		ax2.plot(patient_tier_trimmed['time_hours'],
		         patient_tier_trimmed[patient_id],
		         color='black', linewidth=1, linestyle='--', alpha=0.2,
		         zorder=1)  # Lower zorder so averages are on top

	# Now plot the average lines on top
	ax2.plot(time_series, treatment_tier, color='darkgreen',
	         linewidth=2, marker='o', markersize=4, label='Treatment Tier',
	         alpha=0.8, zorder=2)
	ax2.plot(time_series, standard_tier, color='darkred',
	         linewidth=2, marker='s', markersize=4, label='Standard Tier',
	         alpha=0.8, zorder=2)

	ax2.set_ylabel('Mean Tier Char', fontsize=12, fontweight='bold')
	ax2.grid(True, axis='y', alpha=0.3, linestyle='--')
	ax2.spines['top'].set_visible(False)
	ax2.spines['right'].set_visible(False)

	# Bottom subplot - Valid Recording Hours
	ax3.bar(time_series - offset, treatment_valid, width=width,
	        alpha=0.7, color='green', label='Treatment',
	        edgecolor='black', linewidth=0.5)
	ax3.bar(time_series + offset, standard_valid, width=width,
	        alpha=0.7, color='red', label='Standard',
	        edgecolor='black', linewidth=0.5)

	ax3.set_xlabel('Time Post-Injury (hours)', fontsize=14, fontweight='bold')
	ax3.set_ylabel('Mean Valid Rec. Hours', fontsize=12, fontweight='bold')
	ax3.grid(True, axis='y', alpha=0.3, linestyle='--')
	ax3.spines['top'].set_visible(False)
	ax3.spines['right'].set_visible(False)

	# Improve x-axis labeling - show every bucket
	if len(time_series) > 0:
		ax3.set_xticks(time_series)

	# Add patient lists below figure
	panel_text = (
		f"Treatment patients (N={n_treatment}): {', '.join(treatment_patient_ids)}\n"
		f"Standard patients (N={n_standard}): {', '.join(standard_patient_ids)}"
	)

	fig.text(0.5, 0.02, panel_text, ha='center', fontsize=9, wrap=True)

	plt.tight_layout()
	plt.subplots_adjust(bottom=0.12)  # Make room for panel text

	# Save or show
	if save_path:
		plt.savefig(save_path, dpi=300, bbox_inches='tight')
		print(f"Plot saved to: {save_path}")
	else:
		plt.show()
