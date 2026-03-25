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

	# Create single large plot
	fig, ax1 = plt.subplots(1, 1, figsize=(14, 8))

	# Add overall title
	fig.suptitle('INDICT Cohort: Progression of SD Rates in Treatment and Standard Groups',
	             fontsize=20, fontweight='bold', y=0.98)

	width = bucket_size * 0.35
	offset = width / 2

	# Prepare data for box plots
	treatment_data_by_time = []
	standard_data_by_time = []
	treatment_n_valid = []
	standard_n_valid = []

	for idx, t in enumerate(time_series):
		# Treatment group
		treatment_values = daily_rate_treatment.loc[daily_rate_treatment['time_hours'] == t, treatment_patient_ids].values.flatten()
		treatment_values = treatment_values[~np.isnan(treatment_values)]
		treatment_data_by_time.append(treatment_values)
		treatment_n_valid.append(len(treatment_values))

		# Standard group
		standard_values = daily_rate_standard.loc[daily_rate_standard['time_hours'] == t, standard_patient_ids].values.flatten()
		standard_values = standard_values[~np.isnan(standard_values)]
		standard_data_by_time.append(standard_values)
		standard_n_valid.append(len(standard_values))

	# Create box plots
	box_width = width * 1.2
	bp_treatment = ax1.boxplot([treatment_data_by_time[i] for i in range(len(time_series))],
	                            positions=time_series - offset,
	                            widths=box_width,
	                            patch_artist=True,
	                            showfliers=False,
	                            medianprops=dict(color='darkgreen', linewidth=2.5),
	                            boxprops=dict(facecolor='lightgreen', edgecolor='darkgreen', linewidth=1.5, alpha=0.6),
	                            whiskerprops=dict(color='darkgreen', linewidth=1.5),
	                            capprops=dict(color='darkgreen', linewidth=1.5))

	bp_standard = ax1.boxplot([standard_data_by_time[i] for i in range(len(time_series))],
	                           positions=time_series + offset,
	                           widths=box_width,
	                           patch_artist=True,
	                           showfliers=False,
	                           medianprops=dict(color='darkred', linewidth=2.5),
	                           boxprops=dict(facecolor='lightcoral', edgecolor='darkred', linewidth=1.5, alpha=0.6),
	                           whiskerprops=dict(color='darkred', linewidth=1.5),
	                           capprops=dict(color='darkred', linewidth=1.5))

	# Overlay individual points with jitter
	for idx, t in enumerate(time_series):
		# Treatment points
		if len(treatment_data_by_time[idx]) > 0:
			jitter = np.random.normal(0, width/10, size=len(treatment_data_by_time[idx]))
			x_positions = np.full(len(treatment_data_by_time[idx]), t - offset) + jitter
			ax1.scatter(x_positions, treatment_data_by_time[idx],
			           color='darkgreen', s=60, alpha=0.7,
			           edgecolors='black', linewidth=0.8, zorder=3)

		# Standard points
		if len(standard_data_by_time[idx]) > 0:
			jitter = np.random.normal(0, width/10, size=len(standard_data_by_time[idx]))
			x_positions = np.full(len(standard_data_by_time[idx]), t + offset) + jitter
			ax1.scatter(x_positions, standard_data_by_time[idx],
			           color='darkred', s=60, alpha=0.7,
			           edgecolors='black', linewidth=0.8, zorder=3)

	# Add legend manually
	from matplotlib.patches import Patch
	legend_elements = [Patch(facecolor='lightgreen', edgecolor='darkgreen', label=f'Treatment (N={n_treatment})'),
	                   Patch(facecolor='lightcoral', edgecolor='darkred', label=f'Standard (N={n_standard})')]
	ax1.legend(handles=legend_elements, frameon=True, fontsize=16, loc='upper left')

	ax1.set_ylabel('Daily SD Rate (events/24h)', fontsize=14, fontweight='bold')
	ax1.set_xlabel('Time Post-Randomization (hours)', fontsize=14, fontweight='bold')
	ax1.grid(True, axis='y', alpha=0.3, linestyle='--')
	ax1.spines['top'].set_visible(False)
	ax1.spines['right'].set_visible(False)

	# Set x-axis ticks to exact bucket times
	if len(time_series) > 0:
		ax1.set_xticks(time_series)
		ax1.set_xticklabels([int(t) if t == int(t) else t for t in time_series])

	plt.tight_layout()
	plt.subplots_adjust(bottom=0.35)  # Make room for metadata rows (increased for 3rd row)

	# Add metadata rows below the plot using axis transformation for proper alignment
	# This must be done AFTER tight_layout so axis positions are finalized
	from matplotlib.transforms import blended_transform_factory

	# Create transform: x in data coords, y in axes fraction coords
	trans = blended_transform_factory(ax1.transData, ax1.transAxes)

	# Use first bucket position for label alignment
	label_x_pos = time_series[0] if len(time_series) > 0 else 0

	# Add row label for Treatment Tier (above the data, centered with first bucket)
	ax1.text(label_x_pos, -0.18, 'Treatment Tier (Mean)', ha='center', va='bottom',
	         fontsize=10, fontweight='bold', transform=trans, clip_on=False)

	for idx, t in enumerate(time_series):
		# Treatment value (green) - using blended transform for perfect alignment
		treatment_tier_val = treatment_tier[idx] if not np.isnan(treatment_tier[idx]) else 0
		ax1.text(t, -0.20, f'{treatment_tier_val:.1f}', ha='center', va='center', fontsize=10,
		        color='darkgreen', fontweight='bold', transform=trans, clip_on=False)

		# Standard value (red) - closer to treatment
		standard_tier_val = standard_tier[idx] if not np.isnan(standard_tier[idx]) else 0
		ax1.text(t, -0.23, f'{standard_tier_val:.1f}', ha='center', va='center', fontsize=10,
		        color='darkred', fontweight='bold', transform=trans, clip_on=False)

	# Add row label for ECoG Time (above the data, centered with first bucket)
	ax1.text(label_x_pos, -0.30, 'ECoG Time (Mean Percent)', ha='center', va='bottom',
	         fontsize=10, fontweight='bold', transform=trans, clip_on=False)

	for idx, t in enumerate(time_series):
		# Treatment value (green) - convert to percent
		treatment_valid_val = treatment_valid[idx] if not np.isnan(treatment_valid[idx]) else 0
		treatment_valid_pct = (treatment_valid_val / bucket_size) * 100
		ax1.text(t, -0.32, f'{treatment_valid_pct:.0f}%', ha='center', va='center', fontsize=10,
		        color='darkgreen', fontweight='bold', transform=trans, clip_on=False)

		# Standard value (red) - closer to treatment
		standard_valid_val = standard_valid[idx] if not np.isnan(standard_valid[idx]) else 0
		standard_valid_pct = (standard_valid_val / bucket_size) * 100
		ax1.text(t, -0.35, f'{standard_valid_pct:.0f}%', ha='center', va='center', fontsize=10,
		        color='darkred', fontweight='bold', transform=trans, clip_on=False)

	# Add row label for Number of Valid Rates (above the data, centered with first bucket)
	ax1.text(label_x_pos, -0.42, 'Number of Valid Rates (n)', ha='center', va='bottom',
	         fontsize=10, fontweight='bold', transform=trans, clip_on=False)

	# Calculate N values for each time point
	treatment_n_valid = []
	standard_n_valid = []
	for idx, t in enumerate(time_series):
		# Treatment N
		treatment_values = daily_rate_treatment.loc[daily_rate_treatment['time_hours'] == t, treatment_patient_ids].values.flatten()
		treatment_n = len(treatment_values[~np.isnan(treatment_values)])
		treatment_n_valid.append(treatment_n)

		# Standard N
		standard_values = daily_rate_standard.loc[daily_rate_standard['time_hours'] == t, standard_patient_ids].values.flatten()
		standard_n = len(standard_values[~np.isnan(standard_values)])
		standard_n_valid.append(standard_n)

	for idx, t in enumerate(time_series):
		# Treatment N (green)
		ax1.text(t, -0.44, f'{treatment_n_valid[idx]}', ha='center', va='center', fontsize=10,
		        color='darkgreen', fontweight='bold', transform=trans, clip_on=False)

		# Standard N (red)
		ax1.text(t, -0.47, f'{standard_n_valid[idx]}', ha='center', va='center', fontsize=10,
		        color='darkred', fontweight='bold', transform=trans, clip_on=False)

	# Save or show
	if save_path:
		plt.savefig(save_path, dpi=300, bbox_inches='tight')
		print(f"Plot saved to: {save_path}")
	else:
		plt.show()
