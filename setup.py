from setuptools import setup, find_packages

setup(
    name='espscraper',
    version='1.0.0',
    description='Production-ready ESP Product Detail Scraper',
    author='Your Name',
    author_email='your.email@example.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'selenium',
        'webdriver-manager',
        'beautifulsoup4',
        'python-dotenv',
        'requests',
        'argparse',
    ],
    entry_points={
        'console_scripts': [
            'espscraper=espscraper.__main__:main',
        ],
    },
    python_requires='>=3.7',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
) 