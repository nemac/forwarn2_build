FROM geographica/gdal2:2.4.3
RUN apt-get update && apt-get install wget -y
COPY get_date_netcdf.sh .
COPY rescale_max.sh .

# install pip3 and aws cli
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3 get-pip.py
RUN pip3 install awscli --upgrade

# environment variables for get_date_netcdf.sh
ENV DATETYPE=null
ENV YEAR=null
ENV DOY=null

CMD ./get_date_netcdf.sh $DATETYPE $YEAR $DOY
