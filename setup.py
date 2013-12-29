from setuptools import setup


setup(
    name='epbackup',
    version='0.1',
    scripts=['epbackup.py'],
    author='Horst Gutmann',
    author_email='zerok@zerokspot.com',
    license='BSD',
    install_requires=[
        'boto >= 2.21.0',
        'tempdir >= 0.6',
        'PyYAML >= 3.10',
    ]
)
