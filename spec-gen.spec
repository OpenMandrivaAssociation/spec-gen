Name:		spec-gen
Version:	0.1
Release:	4
Summary:	ROSA RPM spec file generator
Group:		System/Configuration/Packaging
License:	GPLv2+
Url:		http://wiki.rosalab.ru/en/index.php/spec-file-generator
Source0:	https://abf.io/soft/spec-gen-dev/blob/master/spec-gen.py
BuildArch:	noarch
BuildRequires:	python3

%description
Generate spec file on the basis of source tarball analysis.

%prep

%build

%install
mkdir -p %{buildroot}%{_bindir}
install -m 755 %{SOURCE0} %{buildroot}%{_bindir}/

%files
%{_bindir}/*
