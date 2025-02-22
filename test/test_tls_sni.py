import ssl
import subprocess

import pytest
from unit.applications.tls import TestApplicationTLS
from unit.option import option


class TestTLSSNI(TestApplicationTLS):
    prerequisites = {'modules': {'openssl': 'any'}}

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self):
        self._load_conf(
            {
                "listeners": {"*:7080": {"pass": "routes"}},
                "routes": [{"action": {"return": 200}}],
                "applications": {},
            }
        )

    def add_tls(self, cert='default'):
        assert 'success' in self.conf(
            {"pass": "routes", "tls": {"certificate": cert}},
            'listeners/*:7080',
        )

    def remove_tls(self):
        assert 'success' in self.conf({"pass": "routes"}, 'listeners/*:7080')

    def generate_ca_conf(self):
        with open(f'{option.temp_dir}/ca.conf', 'w') as f:
            f.write(
                f"""[ ca ]
default_ca = myca

[ myca ]
new_certs_dir = {option.temp_dir}
database = {option.temp_dir}/certindex
default_md = sha256
policy = myca_policy
serial = {option.temp_dir}/certserial
default_days = 1
x509_extensions = myca_extensions
copy_extensions = copy

[ myca_policy ]
commonName = optional

[ myca_extensions ]
basicConstraints = critical,CA:TRUE"""
            )

        with open(f'{option.temp_dir}/certserial', 'w') as f:
            f.write('1000')

        with open(f'{option.temp_dir}/certindex', 'w') as f:
            f.write('')

    def config_bundles(self, bundles):
        self.certificate('root', False)

        for b in bundles:
            self.openssl_conf(rewrite=True, alt_names=bundles[b]['alt_names'])
            subj = f'/CN={bundles[b]["subj"]}/' if 'subj' in bundles[b] else '/'

            subprocess.check_output(
                [
                    'openssl',
                    'req',
                    '-new',
                    '-subj',
                    subj,
                    '-config',
                    f'{option.temp_dir}/openssl.conf',
                    '-out',
                    f'{option.temp_dir}/{b}.csr',
                    '-keyout',
                    f'{option.temp_dir}/{b}.key',
                ],
                stderr=subprocess.STDOUT,
            )

        self.generate_ca_conf()

        for b in bundles:
            subj = f'/CN={bundles[b]["subj"]}/' if 'subj' in bundles[b] else '/'

            subprocess.check_output(
                [
                    'openssl',
                    'ca',
                    '-batch',
                    '-subj',
                    subj,
                    '-config',
                    f'{option.temp_dir}/ca.conf',
                    '-keyfile',
                    f'{option.temp_dir}/root.key',
                    '-cert',
                    f'{option.temp_dir}/root.crt',
                    '-in',
                    f'{option.temp_dir}/{b}.csr',
                    '-out',
                    f'{option.temp_dir}/{b}.crt',
                ],
                stderr=subprocess.STDOUT,
            )

        self.context = ssl.create_default_context()
        self.context.check_hostname = False
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.context.load_verify_locations(f'{option.temp_dir}/root.crt')

        self.load_certs(bundles)

    def load_certs(self, bundles):
        for bname, bvalue in bundles.items():
            assert 'success' in self.certificate_load(
                bname, bname
            ), f'certificate {bvalue["subj"]} upload'

    def check_cert(self, host, expect):
        resp, sock = self.get_ssl(
            headers={
                'Host': host,
                'Content-Length': '0',
                'Connection': 'close',
            },
            start=True,
        )

        assert resp['status'] == 200
        assert sock.getpeercert()['subject'][0][0][1] == expect

    def test_tls_sni(self):
        bundles = {
            "default": {"subj": "default", "alt_names": ["default"]},
            "localhost.com": {
                "subj": "localhost.com",
                "alt_names": ["alt1.localhost.com"],
            },
            "example.com": {
                "subj": "example.com",
                "alt_names": ["alt1.example.com", "alt2.example.com"],
            },
        }
        self.config_bundles(bundles)
        self.add_tls(["default", "localhost.com", "example.com"])

        self.check_cert('alt1.localhost.com', bundles['localhost.com']['subj'])
        self.check_cert('alt2.example.com', bundles['example.com']['subj'])
        self.check_cert('blah', bundles['default']['subj'])

    def test_tls_sni_no_hostname(self):
        bundles = {
            "localhost.com": {"subj": "localhost.com", "alt_names": []},
            "example.com": {
                "subj": "example.com",
                "alt_names": ["example.com"],
            },
        }
        self.config_bundles(bundles)
        self.add_tls(["localhost.com", "example.com"])

        resp, sock = self.get_ssl(
            headers={'Content-Length': '0', 'Connection': 'close'},
            start=True,
        )
        assert resp['status'] == 200
        assert (
            sock.getpeercert()['subject'][0][0][1]
            == bundles['localhost.com']['subj']
        )

    def test_tls_sni_upper_case(self):
        bundles = {
            "localhost.com": {"subj": "LOCALHOST.COM", "alt_names": []},
            "example.com": {
                "subj": "example.com",
                "alt_names": ["ALT1.EXAMPLE.COM", "*.ALT2.EXAMPLE.COM"],
            },
        }
        self.config_bundles(bundles)
        self.add_tls(["localhost.com", "example.com"])

        self.check_cert('localhost.com', bundles['localhost.com']['subj'])
        self.check_cert('LOCALHOST.COM', bundles['localhost.com']['subj'])
        self.check_cert('EXAMPLE.COM', bundles['localhost.com']['subj'])
        self.check_cert('ALT1.EXAMPLE.COM', bundles['example.com']['subj'])
        self.check_cert('WWW.ALT2.EXAMPLE.COM', bundles['example.com']['subj'])

    def test_tls_sni_only_bundle(self):
        bundles = {
            "localhost.com": {
                "subj": "localhost.com",
                "alt_names": ["alt1.localhost.com", "alt2.localhost.com"],
            }
        }
        self.config_bundles(bundles)
        self.add_tls(["localhost.com"])

        self.check_cert('domain.com', bundles['localhost.com']['subj'])
        self.check_cert('alt1.domain.com', bundles['localhost.com']['subj'])

    def test_tls_sni_wildcard(self):
        bundles = {
            "localhost.com": {"subj": "localhost.com", "alt_names": []},
            "example.com": {
                "subj": "example.com",
                "alt_names": ["*.example.com", "*.alt.example.com"],
            },
        }
        self.config_bundles(bundles)
        self.add_tls(["localhost.com", "example.com"])

        self.check_cert('example.com', bundles['localhost.com']['subj'])
        self.check_cert('www.example.com', bundles['example.com']['subj'])
        self.check_cert('alt.example.com', bundles['example.com']['subj'])
        self.check_cert('www.alt.example.com', bundles['example.com']['subj'])
        self.check_cert('www.alt.example.ru', bundles['localhost.com']['subj'])

    def test_tls_sni_duplicated_bundle(self):
        bundles = {
            "localhost.com": {
                "subj": "localhost.com",
                "alt_names": ["localhost.com", "alt2.localhost.com"],
            }
        }
        self.config_bundles(bundles)
        self.add_tls(["localhost.com", "localhost.com"])

        self.check_cert('localhost.com', bundles['localhost.com']['subj'])
        self.check_cert('alt2.localhost.com', bundles['localhost.com']['subj'])

    def test_tls_sni_same_alt(self):
        bundles = {
            "localhost": {"subj": "subj1", "alt_names": "same.altname.com"},
            "example": {"subj": "subj2", "alt_names": "same.altname.com"},
        }
        self.config_bundles(bundles)
        self.add_tls(["localhost", "example"])

        self.check_cert('localhost', bundles['localhost']['subj'])
        self.check_cert('example', bundles['localhost']['subj'])

    def test_tls_sni_empty_cn(self):
        bundles = {"localhost": {"alt_names": ["alt.localhost.com"]}}
        self.config_bundles(bundles)
        self.add_tls(["localhost"])

        resp, sock = self.get_ssl(
            headers={
                'Host': 'domain.com',
                'Content-Length': '0',
                'Connection': 'close',
            },
            start=True,
        )

        assert resp['status'] == 200
        assert sock.getpeercert()['subjectAltName'][0][1] == 'alt.localhost.com'

    def test_tls_sni_invalid(self):
        self.config_bundles({"localhost": {"subj": "subj1", "alt_names": ''}})
        self.add_tls(["localhost"])

        def check_certificate(cert):
            assert 'error' in self.conf(
                {"pass": "routes", "tls": {"certificate": cert}},
                'listeners/*:7080',
            )

        check_certificate('')
        check_certificate('blah')
        check_certificate([])
        check_certificate(['blah'])
        check_certificate(['localhost', 'blah'])
        check_certificate(['localhost', []])
