import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def plot_tier_comparison(output_dict, save_path=None):
	"""
	Creates a scatter plot comparing SD rates across different tiers and treatment groups.
	Shows median values with interquartile ranges and individual patient data points.

	Args:
		output_dict: The output dictionary from INDICT_XLSX_Analysis
		save_path: Optional path to save the figure. If None, will display the plot.
	"""

	# Define the categories to compare
	categories = ['Standard', 'Tier1', 'Tier2', 'Tier3']
	category_labels = ['Standard', 'Tier 1', 'Tier 2', 'Tier 3']

	# Collect data for each category
	category_data = {cat: [] for cat in categories}

	for patient_id, patient_data in output_dict.items():
		for cat in categories:
			if cat in patient_data['Summary']:
				sd_rate = patient_data['Summary'][cat]['daily_SD_rate']
				# Only include non-NaN values
				if not np.isnan(sd_rate):
					category_data[cat].append(sd_rate)

	# Calculate statistics for each category
	medians = []
	q25s = []
	q75s = []
	n_values = []

	for cat in categories:
		data = category_data[cat]
		if len(data) > 0:
			medians.append(np.median(data))
			q25s.append(np.percentile(data, 25))
			q75s.append(np.percentile(data, 75))
			n_values.append(len(data))
		else:
			medians.append(np.nan)
			q25s.append(np.nan)
			q75s.append(np.nan)
			n_values.append(0)

	medians = np.array(medians)
	q25s = np.array(q25s)
	q75s = np.array(q75s)

	# Create figure
	fig, ax = plt.subplots(figsize=(10, 8))

	# Define x-positions for each category
	x_positions = np.arange(len(categories))

	# Define colors for each category
	colors = ['gray', '#FFD700', '#FFA500', '#FF6B6B']  # Gray, Gold, Orange, Red

	# Plot individual patient points with jitter
	for i, cat in enumerate(categories):
		data = category_data[cat]
		if len(data) > 0:
			# Add jitter to x-position
			jitter = np.random.uniform(-0.15, 0.15, size=len(data))
			ax.scatter([x_positions[i]] * len(data) + jitter, data,
			          color=colors[i], s=60, alpha=0.4, edgecolors='black', linewidth=0.5, zorder=1)

	# Plot medians with IQR error bars
	yerr = [medians - q25s, q75s - medians]

	ax.errorbar(x_positions, medians, yerr=yerr,
	           fmt='o', markersize=12, color='black', ecolor='black',
	           capsize=8, capthick=2, linewidth=2, zorder=3,
	           label='Median with IQR')

	# Add median markers with category colors
	ax.scatter(x_positions, medians, s=150, c=colors, edgecolors='black',
	          linewidth=2, zorder=4, alpha=0.8)

	# Add N values above each point and median values next to the point
	y_max = ax.get_ylim()[1]
	for i, (x, median, q75, n) in enumerate(zip(x_positions, medians, q75s, n_values)):
		if n > 0 and not np.isnan(q75):
			ax.text(x, q75 + (y_max * 0.05), f'n={n}',
			       ha='center', va='bottom', fontsize=10, fontweight='bold')

		# Add median value next to the median point
		if not np.isnan(median):
			ax.text(x + 0.25, median, f'{median:.2f}',
			       ha='left', va='center', fontsize=10, fontweight='bold',
			       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.8))

	# Styling
	ax.set_xticks(x_positions)
	ax.set_xticklabels(category_labels, fontsize=12, fontweight='bold')
	ax.set_ylabel('Daily SD Rate (events/24h)', fontsize=14, fontweight='bold')
	ax.set_xlabel('Treatment Category', fontsize=14, fontweight='bold')
	ax.set_title('Comparison of Daily SD Rates Across Treatment Tiers',
	            fontsize=16, fontweight='bold', pad=20)

	# Grid
	ax.grid(True, axis='y', alpha=0.3, linestyle='--')
	ax.spines['top'].set_visible(False)
	ax.spines['right'].set_visible(False)

	# Add legend
	from matplotlib.patches import Patch
	legend_elements = [
		plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='black',
		          markersize=10, markeredgecolor='black', label='Median'),
		plt.Line2D([0], [0], color='black', linewidth=2, label='IQR (25th-75th percentile)'),
		Patch(facecolor='gray', alpha=0.4, edgecolor='black', label='Individual Patients')
	]
	ax.legend(handles=legend_elements, loc='upper right', fontsize=10, framealpha=0.9)

	# Add horizontal line at y=0 for reference
	ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)

	plt.tight_layout()

	# Save or show
	if save_path:
		plt.savefig(save_path, dpi=300, bbox_inches='tight')
		print(f"Plot saved to: {save_path}")
	else:
		plt.show()
