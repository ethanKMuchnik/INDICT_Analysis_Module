from setuptools import setup, find_packages

setup(
		name="analysis_module",
		version="0.1.0",
		packages=find_packages(),
		install_requires=[
				"pandas",
				"numpy",
				"openpyxl"
		],
		author="Your Name",
		description="INDICT XLSX analysis tools",
		python_requires=">=3.7"
)

