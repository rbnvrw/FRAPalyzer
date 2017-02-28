from setuptools import setup

VERSION = '0.0.1'

if __name__ == '__main__':
    setup(
        name='frapalyzer',
        packages=['frapalyzer'],
        install_requires=[
            'numpy>=1.6.2, <2.0',
            'nd2reader>=2.1.3'
        ],
        version=VERSION,
        description='Analyze Nikon ND2 stimulation FRAP experiments automatically',
        author='Ruben Verweij',
        author_email='verweij@physics.leidenuniv.nl',
        url='https://github.com/rbnvrw/frapalyzer',
        download_url='https://github.com/rbnvrw/frapalyzer/tarball/%s' % VERSION,
        keywords=['nd2', 'nikon', 'microscopy', 'NIS Elements', 'FRAP'],
        classifiers=['Development Status :: 3 - Alpha',
                     'Intended Audience :: Science/Research',
                     'License :: Freely Distributable',
                     'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
                     'Operating System :: POSIX :: Linux',
                     'Programming Language :: Python :: 2.7',
                     'Programming Language :: Python :: 3.4',
                     'Topic :: Scientific/Engineering',
                     ]
    )
