# Imported Libraries
import pandas as pd
import numpy as np 
import json 
import re 
from openpyxl.styles import Font, PatternFill
# -------


# Simple cosmetics 
def adjust_column_widths(worksheet):
  """Auto-adjust column widths based on content"""
  for column in worksheet.columns:
	  max_length = 0
	  column_letter = column[0].column_letter
	  for cell in column:
		  try:
			  if cell.value:
				  max_length = max(max_length, len(str(cell.value)))
		  except:
			  pass
	  adjusted_width = min(max_length + 2, 50)  # Cap at 50 to avoid super wide columns
	  worksheet.column_dimensions[column_letter].width = adjusted_width


# Load the master file (with patient id, treatment group and injury date)
def format_master_file(input_master_file):

	master_file = pd.ExcelFile(input_master_file)
	master_sheet =  pd.read_excel(master_file, sheet_name=0, header=None)
	master_sheet = master_sheet.iloc[1:].reset_index(drop=True) #Shift one down
	master_sheet.columns = ['patient_id','treatment_group','injury_datetime']
	master_sheet = master_sheet.set_index('patient_id')

	return master_sheet




# Get A and D col of event data with set rules 
def extract_events_from_single_sheet(input_sheet,patient_injury_datetime):

	# Get tupe and datetime
	event_data = input_sheet.iloc[:, [0, 3]].copy()
	event_data.columns = ['event_type', 'datetime']
		
	# Drop na event rows 
	event_data = event_data.dropna(subset=['event_type'])
		
	# Subtract Time of injury
	event_data['datetime'] = event_data['datetime'].dt.round('s') #Reads data and rounds
	event_data['time_post_injury'] = ((event_data['datetime'] -patient_injury_datetime).dt.total_seconds() / 3600).round(2)



	# Structured replacements 
	event_data['event_type'] = event_data['event_type'].replace('sCSD', 'CSD')
	event_data['event_type'] = event_data['event_type'].replace('ISD/CSD', 'ISD')
	event_data['event_type'] = event_data['event_type'].replace('CSD/ISD', 'ISD')


	return event_data

# Hours with 2 decimals of differnece btween datetimes
def datetime_relative_to_injury(datetime_of_interest,injury_datetime):
	return round(((datetime_of_interest - injury_datetime).total_seconds() / 3600),2)

def get_randomization_time(input_sheet,patient_injury_datetime):
	randomization_text = input_sheet.iloc[0,10]
	assert randomization_text == 'Randomize'
	randomization_datetime = input_sheet.iloc[0,11]
	return datetime_relative_to_injury(randomization_datetime,patient_injury_datetime),randomization_datetime

def check_time_inclusion_in_list(time_hours,range_list):
	#Range list e.g [(10,20),(34.2,50),(74,80)], time_hours = 6.5 --> false

	for start,end in range_list:
		if (start <= time_hours) and (end > time_hours):
			return True 

	return False

def compute_bucketed_events(event_data,bucket_size,max_time,temp_dict,time_reference_key = 'time_post_injury',min_time = 0,fixed_offset = 0):
	time_hours = np.arange(min_time,max_time,bucket_size)
	valid_hours = [] 
	event_counts = []
	tier_characters = []
	daily_SD_rate = []



	for abs_time in time_hours:
		# shift time 

		t = abs_time + fixed_offset
		segment_time_series = [(t,t + bucket_size)]

		# Valid hours
		valid_hours_ind = series_overlap(segment_time_series,temp_dict['Epochs']['Valid'])
		valid_hours.append(round(valid_hours_ind,2))

		# Compute event count
		boolean_events = ((event_data[time_reference_key] >= t) & (event_data[time_reference_key] < t + bucket_size))
		num_events_ind = boolean_events.sum()
		event_counts.append(num_events_ind)

		# Compute tier charachter - note def and if  
		tier1_hours = series_overlap(segment_time_series,temp_dict['Epochs']['Tier1'])
		tier2_hours = series_overlap(segment_time_series,temp_dict['Epochs']['Tier2'])
		tier3_hours = series_overlap(segment_time_series,temp_dict['Epochs']['Tier3'])

		tier_character_ind = (tier1_hours + 2*tier2_hours + 3*tier3_hours)/bucket_size

		# note change
		if valid_hours_ind == 0:
			tier_character_ind = np.nan
			
		tier_characters.append(round(tier_character_ind,2))

		# Compute daily SD rate = [SDs/(valid hours)] * 24
		daily_rate_ind = round(24*num_events_ind/valid_hours_ind,2) if valid_hours_ind > 0 else np.nan

		daily_SD_rate.append(daily_rate_ind)

	# Create dataframe
	bucketed_events = pd.DataFrame({
	  'time_hours': time_hours,
	  'valid_recording_hours': valid_hours,
	  'num_events': event_counts,
	  'tier_character':tier_characters,
	  'daily_SD_rate':daily_SD_rate
	})

	return bucketed_events

def series_overlap(series1,series2):
	# Format both [(20,40)] or [(20,30),(60,90)] etc

	total_overlap = 0
	for ind_range1 in series1:
		for ind_range2 in series2:
			overlap_start = max(ind_range1[0],ind_range2[0])
			overlap_end = min(ind_range1[1],ind_range2[1])
			overlap = max(0, overlap_end - overlap_start)
			total_overlap += overlap

	return total_overlap

def INDICT_XLSX_Analysis(input_scoring_file,input_master_file,bucket_size = 6, max_time = 240):

	"""
	Inputs: Scoring and master file with presumed format 
	Outputs:
		saves: 	eventCSV per patient 
				dailyCSV per patient
				bucketedCSV per patient 
				globalBucketdCSV
				 output_dictionary
					-patientId
						...
	"""

	# load the scoring data (all of it from excel) into dict format
	xlsx_file = pd.ExcelFile(input_scoring_file)
	input_sheets_dict = pd.read_excel(xlsx_file, sheet_name=None, header=None)

	# Input master file and format 
	master_sheet = format_master_file(input_master_file)

	# Create empty output to store data
	output_dictionary = dict()


	#Iterate through the patients 
	for patient_id, relevant_sheet in input_sheets_dict.items():
		print('Analyzing patient: ', patient_id)
		temp_dict = {}

		# Reference master list 
		patient_injury_datetime = master_sheet.loc[patient_id, 'injury_datetime']
		patient_treatment_group = master_sheet.loc[patient_id, 'treatment_group']
		if patient_treatment_group == 'SD-Guided':
			patient_treatment_group = 'Treatment'
		temp_dict['patient_injury_datetime'] = patient_injury_datetime		
		# Get event data 
		event_data = extract_events_from_single_sheet(relevant_sheet,patient_injury_datetime)


		# Randomization time
		temp_dict['patient_treatment_group'] = patient_treatment_group
		temp_dict['randomization_hours'],randomization_datetime = get_randomization_time(relevant_sheet,patient_injury_datetime)
		temp_dict['Epochs'] = {'Valid':[],'Tier1':[],'Tier2':[],'Tier3':[]}
		valid_tier_names = ['Tier1','Tier2','Tier3']
		temp_dict['randomization_datetime'] = randomization_datetime		


		# Events DEFAULT to standard tier - unless a treatment group overrides that or prerandom
		event_data['momentary_treatment_tier'] = 'Standard'
		event_data.loc[event_data['time_post_injury'] < temp_dict['randomization_hours'], 'momentary_treatment_tier'] ='Pre-Randomization'


		# Obtain tier data if in treatment group
		if patient_treatment_group == 'Treatment':
			
			# first we extract the tier data KLM 2/1 + 
			current_row = 1 # 2nd in excel
			while True:
				# Check if name is valid 
				this_tier_name = relevant_sheet.iloc[current_row,10]
				if this_tier_name in valid_tier_names:

					this_epoch_start = datetime_relative_to_injury(relevant_sheet.iloc[current_row,11],patient_injury_datetime)
					this_epoch_end = datetime_relative_to_injury(relevant_sheet.iloc[current_row,12],patient_injury_datetime)

					# check the time diff is > 1 min (for valid t delta) - CIN 1011 - rememebr units hours now
					if this_epoch_end - this_epoch_start > 1/60:
						temp_dict['Epochs'][this_tier_name].append((this_epoch_start,this_epoch_end))

					current_row +=1
				else:
					break

			# Assign each event a tier based on our epochs data
			for index, row in event_data.iterrows():
				event_time = row['time_post_injury']

				# Inclusion count to be sure events are only in one tier or none
				inclusion_count = 0 

				# Check each tier 
				if check_time_inclusion_in_list(event_time,temp_dict['Epochs']['Tier1']):
					event_data.at[index, 'momentary_treatment_tier'] = 'Tier1'
					inclusion_count += 1
				if check_time_inclusion_in_list(event_time,temp_dict['Epochs']['Tier2']):
					event_data.at[index, 'momentary_treatment_tier'] = 'Tier2'
					inclusion_count += 1
				if check_time_inclusion_in_list(event_time,temp_dict['Epochs']['Tier3']):
					event_data.at[index, 'momentary_treatment_tier'] = 'Tier3'
					inclusion_count += 1

		
				assert inclusion_count < 2


		# Save the event csv
		temp_dict['event_data_df'] = event_data

		# Establish valid recording epochs 
		row_counter_validity = 0 

		while True:
		
			startText = relevant_sheet.iloc[row_counter_validity,5]
			endText = relevant_sheet.iloc[row_counter_validity + 1,5]
			if startText == 'Start' and endText == 'Finish':
				start_datetime = relevant_sheet.iloc[row_counter_validity,8]
				end_datetime = relevant_sheet.iloc[row_counter_validity + 1,8]

				start_hours = datetime_relative_to_injury(start_datetime,patient_injury_datetime)
				end_hours = datetime_relative_to_injury(end_datetime,patient_injury_datetime)

				temp_dict['Epochs']['Valid'].append((start_hours,end_hours))
				
				# Update counter and break if too large 
				row_counter_validity+=2
				if row_counter_validity + 1 >= len(relevant_sheet):
					break
			else:
				break
		
		# Compute both daily and bucketed events 
		daily_events = compute_bucketed_events(event_data,24,max_time,temp_dict)
		temp_dict['daily_events_df'] = daily_events


		bucketed_events = compute_bucketed_events(event_data,bucket_size,max_time,temp_dict)
		temp_dict['bucketed_events_df'] = bucketed_events
		
		# randomization centered time
		bucketed_events_post_random = compute_bucketed_events(event_data,6,72,temp_dict,min_time = -24,fixed_offset = temp_dict['randomization_hours'])
		temp_dict['bucketed_events_df_random_centered'] = bucketed_events_post_random


		
		# Add stats, rates, tier validity overlaps, etc to json
		total_valid_length = series_overlap(temp_dict['Epochs']['Valid'],[(temp_dict['randomization_hours'],1000)])
		total_valid_length = round(total_valid_length,2)

		temp_dict['Summary'] = dict()

		# Get valid time intesections
		for tier_name in ['Tier1','Tier2','Tier3']:
			valid_tier_time = round(series_overlap(temp_dict['Epochs'][tier_name],temp_dict['Epochs']['Valid']),2)
			temp_dict['Summary'][tier_name] = {'valid_hours':valid_tier_time}
		
		temp_dict['Summary']['All'] = {'valid_hours':total_valid_length}

		# Get counts
		# For counts modify the event data 
		event_data_no_prerandom_events = event_data[event_data['momentary_treatment_tier'] != 'Pre-Randomization'].copy()

		for tier_name in ['Tier1','Tier2','Tier3',]:
			num_events_tier = int((event_data_no_prerandom_events['momentary_treatment_tier'] == tier_name).sum())
			temp_dict['Summary'][tier_name]['num_events'] = num_events_tier

		temp_dict['Summary']['All']['num_events'] = len(event_data_no_prerandom_events)


		# Now daily rates
		for tier_name in ['Tier1','Tier2','Tier3','All']:
			if temp_dict['Summary'][tier_name]['valid_hours'] > 0:
				temp_dict['Summary'][tier_name]['daily_SD_rate'] = round(24 *  temp_dict['Summary'][tier_name]['num_events'] / temp_dict['Summary'][tier_name]['valid_hours'],2)
			else:
				temp_dict['Summary'][tier_name]['daily_SD_rate'] = np.nan
		# Assign temp dict to this relevant spot for patient

		output_dictionary[patient_id] = temp_dict

	return output_dictionary

	

def export_INDICT_data(results_dict,save_path):


	# Create excel writer for outputs....
	excel_writer = pd.ExcelWriter(save_path + 'event_tables.xlsx',engine = 'openpyxl')


	for patient_id in results_dict.keys():

		temp_dict = results_dict[patient_id]

		# Save the events to a sheet
		temp_dict['event_data_df'].to_excel(excel_writer, sheet_name=patient_id, index=False, startrow=0, startcol=0)

		daily_start_col = 5
		temp_dict['daily_events_df'].to_excel(excel_writer, sheet_name=patient_id, index=False, startrow=0,startcol=daily_start_col)

		bucketed_start_col = 11
		temp_dict['bucketed_events_df_random_centered'].to_excel(excel_writer, sheet_name=patient_id, index=False, startrow=0,startcol=bucketed_start_col)

		# Add individual stats
		worksheet = excel_writer.sheets[patient_id]

		worksheet['R1'] = 'Treatment Group'
		worksheet['S1'] = temp_dict['patient_treatment_group']
		worksheet['S1'].font = Font(bold=True)
		worksheet['S1'].fill = PatternFill(start_color='d4675f', end_color='d4675f', fill_type='solid')


		worksheet['R2'] = 'Time of Injury'
		worksheet['S2'] = temp_dict['patient_injury_datetime']

		worksheet['R4'] = 'Randomization Datetime'
		worksheet['S4'] = temp_dict['randomization_datetime']

		worksheet['R5'] = 'Randomization Hours'
		worksheet['S5'] = temp_dict['randomization_hours']


		worksheet['R7'] = 'Valid Epochs'
		worksheet['S7'] = str(temp_dict['Epochs']['Valid'])

		worksheet['R9'] = 'Tier 1 Epochs'
		worksheet['S9'] = str(temp_dict['Epochs']['Tier1'])

		worksheet['R10'] = 'Tier 2 Epochs'
		worksheet['S10'] = str(temp_dict['Epochs']['Tier2'])

		worksheet['R11'] = 'Tier 3 Epochs'
		worksheet['S11'] = str(temp_dict['Epochs']['Tier3'])


		worksheet['S15'] = 'Event Number'
		worksheet['T15'] = 'Valid Hours'
		worksheet['U15'] = 'SD Rate (daily)'

		worksheet['R16'] = 'All'
		worksheet['S16'] = temp_dict['Summary']['All']['num_events']
		worksheet['T16'] = temp_dict['Summary']['All']['valid_hours']
		worksheet['U16'] = temp_dict['Summary']['All']['daily_SD_rate']

		worksheet['R18'] = 'Tier1'
		worksheet['S18'] = temp_dict['Summary']['Tier1']['num_events']
		worksheet['T18'] = temp_dict['Summary']['Tier1']['valid_hours']
		worksheet['U18'] = temp_dict['Summary']['Tier1']['daily_SD_rate']


		worksheet['R19'] = 'Tier2'
		worksheet['S19'] = temp_dict['Summary']['Tier2']['num_events']
		worksheet['T19'] = temp_dict['Summary']['Tier2']['valid_hours']
		worksheet['U19'] = temp_dict['Summary']['Tier2']['daily_SD_rate']

		worksheet['R20'] = 'Tier3'
		worksheet['S20'] = temp_dict['Summary']['Tier3']['num_events']
		worksheet['T20'] = temp_dict['Summary']['Tier3']['valid_hours']
		worksheet['U20'] = temp_dict['Summary']['Tier3']['daily_SD_rate']
		

		#-_-_-_-_

		adjust_column_widths(excel_writer.sheets[f'{patient_id}'])

	excel_writer.close()

 
