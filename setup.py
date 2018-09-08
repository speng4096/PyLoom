from distutils.core import setup

setup(
    name='pyloom',
    version='0.0.7',
    packages=['pyloom'],
    url='https://pyloom.com',
    license='https://opensource.org/licenses/MIT',
    author='pyloom',
    author_email='ss@uutoto.com',
    description='古老的东方有一条虫，它的名字叫爬龙。',
    entry_points={
        'console_scripts': [
            'pyloom = pyloom.entry:main'
        ]
    },
    install_requires=[
        'redis',
        'cryptography >= 2.2.1',
        'requests[security, socks] >= 2.10.0',
        'bs4',
        'lxml',
        'furl',
        'simplejson',
        'checksumdir',
        'docutils',  # python-daemon的依赖
        'python-daemon',
        'tabulate',
        'psutil'
    ]
)
