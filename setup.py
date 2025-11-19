from setuptools import setup, find_packages

setup(
    name="smart-organizer",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "watchdog",  # For real-time monitoring
    ],
    entry_points={
        'console_scripts': [
            'organize=smart_organizer.cli:main',  # Creates the 'organize' command
        ],
    },
    author="Akshay Nayak",
    description="A smart, automated file organizer with undo and real-time monitoring capabilities.",
)