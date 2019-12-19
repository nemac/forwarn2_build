FROM geographica/gdal2:2.4.3
RUN apt-get update && apt-get install wget -y
COPY netcdf.py .
#COPY get_date_netcdf.sh .
#COPY rescale_max.sh .

#install pip3 and aws cli
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3 get-pip.py
RUN pip3 install python3-wget
#RUN pip3 install awscli --upgrade
RUN pip3 install braceexpand

CMD ["python3", "netcdf.py"]
#CMD ["./get_date_netcdf.sh", "std", "2019", "001"]
