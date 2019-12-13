FROM geographica/gdal2:2.4.3
RUN apt-get update && apt-get install wget -y
WORKDIR /tmp/build

#install pip3 and aws cli
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3 get-pip.py
RUN pip3 install awscli --upgrade
CMD ["aws", "--version"]

#CMD ["./get_date_netcdf.sh", "std", "2019", "001"]
