from setuptools import setup

with open("README.md", encoding="utf-8") as readme:
    long_description = readme.read()

setup(
    name="Volto",
    version="0.1.0",
    description='MS VOLT .vtp to AFDKO .fea OpenType Layout converter',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/TiroTypeworks/Volto',
    author='Khaled Hosny',
    author_email='khaledhosny@eglug.org',
    license='MIT',
    platforms=['Any'],
    package_dir={'': 'Lib'},
    packages=['volto'],
    entry_points={
        'console_scripts': ['volto = volto:main'],
    },
    install_requires=['fonttools>=3.40.0'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Text Processing :: Fonts',
        'Topic :: Multimedia :: Graphics',
        'Topic :: Multimedia :: Graphics :: Graphics Conversion',
    ],
)
