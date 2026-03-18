import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def plot_single_patient(output_dict, patient_id, save_path=None):
	"""
	Creates a single patient plot showing SD events, tier epochs, and valid recording time.

	Args:
		output_dict: The output dictionary from INDICT_XLSX_Analysis
		patient_id: The patient ID to plot
		save_path: Optional path to save the figure. If None, will display the plot.
	"""

	if patient_id not in output_dict:
		print(f"Error: Patient ID '{patient_id}' not found in output dictionary")
		return

	patient_data = output_dict[patient_id]
	event_data = patient_data['event_data_df']
	epochs = patient_data['Epochs']
	treatment_group = patient_data['patient_treatment_group']

	# Determine max time for x-axis
	max_time = event_data['time_post_injury'].max() if len(event_data) > 0 else 240
	if epochs['Valid']:
		max_valid_time = max([end for start, end in epochs['Valid']])
		max_time = max(max_time, max_valid_time)

	# Create figure with subplots
	fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10),
	                                     sharex=True, gridspec_kw={'height_ratios': [1, 1.5, 1.5]})

	# Add overall title
	fig.suptitle(f'Patient {patient_id} - {treatment_group} Group',
	             fontsize=18, fontweight='bold', y=0.995)

	# ===== Top subplot - SD Events =====
	if len(event_data) > 0:
		# Plot each event as a dot at y=1
		ax1.scatter(event_data['time_post_injury'], [1] * len(event_data),
		           color='black', s=80, marker='|', linewidths=3, alpha=0.7)

	ax1.set_ylim(0, 2)
	ax1.set_ylabel('SD Events', fontsize=12, fontweight='bold')
	ax1.set_yticks([])
	ax1.spines['left'].set_visible(False)
	ax1.spines['top'].set_visible(False)
	ax1.spines['right'].set_visible(False)
	ax1.grid(True, axis='x', alpha=0.3, linestyle='--')

	# Add event count text
	ax1.text(0.02, 0.95, f'Total Events: {len(event_data)}',
	        transform=ax1.transAxes, fontsize=11, verticalalignment='top',
	        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

	# ===== Middle subplot - Tier Epochs =====
	tier_colors = {
		'Tier1': '#FFD700',  # Gold (bottom)
		'Tier2': '#FFA500',  # Orange (middle)
		'Tier3': '#FF6B6B',  # Red (top)
	}
	tier_y_positions = {'Tier1': 0.1, 'Tier2': 0.4, 'Tier3': 0.7}

	# Plot tier epochs as horizontal bars
	for tier_name, color in tier_colors.items():
		if tier_name in epochs and epochs[tier_name]:
			y_pos = tier_y_positions[tier_name]
			for start, end in epochs[tier_name]:
				width = end - start
				rect = Rectangle((start, y_pos), width, 0.2,
				                linewidth=1, edgecolor='black',
				                facecolor=color, alpha=0.7)
				ax2.add_patch(rect)

	ax2.set_ylim(0, 1)
	ax2.set_ylabel('Treatment Tiers', fontsize=12, fontweight='bold')
	ax2.set_yticks([0.2, 0.5, 0.8])
	ax2.set_yticklabels(['Tier 1', 'Tier 2', 'Tier 3'])
	ax2.spines['top'].set_visible(False)
	ax2.spines['right'].set_visible(False)
	ax2.grid(True, axis='x', alpha=0.3, linestyle='--')

	# ===== Bottom subplot - Valid Recording Time =====
	# Plot valid epochs in green
	for start, end in epochs['Valid']:
		width = end - start
		rect = Rectangle((start, 0.3), width, 0.4,
		                linewidth=1, edgecolor='black',
		                facecolor='green', alpha=0.6)
		ax3.add_patch(rect)

	# Calculate and plot gaps (invalid time) in red
	if epochs['Valid']:
		sorted_valid = sorted(epochs['Valid'])
		# Gap before first valid epoch
		if sorted_valid[0][0] > 0:
			rect = Rectangle((0, 0.3), sorted_valid[0][0], 0.4,
			                linewidth=1, edgecolor='black',
			                facecolor='red', alpha=0.6)
			ax3.add_patch(rect)

		# Gaps between valid epochs
		for i in range(len(sorted_valid) - 1):
			gap_start = sorted_valid[i][1]
			gap_end = sorted_valid[i + 1][0]
			if gap_end > gap_start:
				width = gap_end - gap_start
				rect = Rectangle((gap_start, 0.3), width, 0.4,
				                linewidth=1, edgecolor='black',
				                facecolor='red', alpha=0.6)
				ax3.add_patch(rect)

		# Gap after last valid epoch
		if sorted_valid[-1][1] < max_time:
			gap_width = max_time - sorted_valid[-1][1]
			rect = Rectangle((sorted_valid[-1][1], 0.3), gap_width, 0.4,
			                linewidth=1, edgecolor='black',
			                facecolor='red', alpha=0.6)
			ax3.add_patch(rect)

	ax3.set_ylim(0, 1)
	ax3.set_ylabel('Recording Status', fontsize=12, fontweight='bold')
	ax3.set_yticks([0.5])
	ax3.set_yticklabels(['Valid/Invalid'])
	ax3.set_xlabel('Time Post-Injury (hours)', fontsize=14, fontweight='bold')
	ax3.spines['top'].set_visible(False)
	ax3.spines['right'].set_visible(False)
	ax3.grid(True, axis='x', alpha=0.3, linestyle='--')

	# Set x-axis limits
	ax3.set_xlim(0, max_time * 1.05)

	# Add legend for valid/invalid recording
	from matplotlib.patches import Patch
	legend_elements = [
		Patch(facecolor='green', alpha=0.6, edgecolor='black', label='Valid Recording'),
		Patch(facecolor='red', alpha=0.6, edgecolor='black', label='Invalid Recording')
	]
	ax3.legend(handles=legend_elements, loc='upper right', fontsize=9)

	# Add summary statistics text box
	summary_text = f"Randomization Time: {patient_data['randomization_hours']:.2f} hrs\n"
	summary_text += f"Total Valid Hours: {patient_data['Summary']['All']['valid_hours']:.2f}\n"
	summary_text += f"Daily SD Rate: {patient_data['Summary']['All']['daily_SD_rate']:.2f}"

	fig.text(0.98, 0.02, summary_text, ha='right', fontsize=9,
	        bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

	plt.tight_layout()
	plt.subplots_adjust(bottom=0.08)

	# Save or show
	if save_path:
		plt.savefig(save_path, dpi=300, bbox_inches='tight')
		print(f"Plot saved to: {save_path}")
	else:
		plt.show()
