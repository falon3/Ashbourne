# Ashbourn
Main Django project located in django-server directory    

Setup:
* Clone this repository     
* cd into django-server directory    
* Use [Virtualenv](https://virtualenv.pypa.io/en/stable/) to create a custom python environment where you clone this repository locally 
* Additional requirements likely needed before pip install requirments.txt:    
      the required geospatial libraries:    
      > $ sudo apt-get install binutils libproj-dev gdal-bin    
            
      GEOS download and configure:        
      > $ wget http://download.osgeo.org/geos/geos-3.4.2.tar.bz2      
      > $ tar xjf geos-3.4.2.tar.bz2  
      > $ cd geos-3.4.2   
      > $ ./configure     
      > $ make            
      > $ sudo make install     
      > $ cd .. 
            
      [PROJ.4](https://github.com/OSGeo/proj.4/wiki/) is a library for converting geospatial data to different coordinate reference systems:   
      >  wget http://download.osgeo.org/proj/proj-4.9.1.tar.gz     
      > $ wget http://download.osgeo.org/proj/proj-datumgrid-1.5.tar.gz   
      Next, untar the source code archive, and extract the datum shifting files in the nad subdirectory. This must be done prior to configuration:    
      > $ tar xzf proj-4.9.1.tar.gz   
      > $ cd proj-4.9.1/nad     
      > $ tar xzf ../../proj-datumgrid-1.5.tar.gz 
      > $ cd ..     
      Finally, configure, make and install PROJ.4:    
      > $ ./configure     
      > $ make      
      > $ sudo make install     
      > $ cd ..     
      
      GDAL open source geospatial library that has support for reading most vector and raster spatial data formats:     
      > $ wget http://download.osgeo.org/gdal/1.11.2/gdal-1.11.2.tar.gz   
      > $ tar xzf gdal-1.11.2.tar.gz  
      > $ cd gdal-1.11.2  
      Configure, make and install:  
      > $ ./configure --with-python     
      > $ make # Go get some coffee, this takes a while.      
      > $ sudo make install     
      > $ cd ..
      
* Install postgis for your machine: http://postgis.net/install/   
      [for Ubuntu](http://trac.osgeo.org/postgis/wiki/UsersWikiPostGIS22UbuntuPGSQL95Apt) first check what release you have:                
      > $ sudo lsb_release -a   
                        
      Then lookup your release for <i>your_tagname</i> [here](http://www.postgresql.org/download/linux/ubuntu/) and insert:          
      sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt <i>your_tagname</i>-pgdg main" >> /etc/apt/sources.list'               
                        
      Add Keys:                  
      > $ wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | sudo apt-key add -   
      > $ sudo apt-get update   
            
      Install postgresql 9.5, PostGIS 2.2, PGAdmin3, pgRouting 2.1 :      
      > $ sudo apt-get install postgresql-9.5-postgis-2.2 pgadmin3 postgresql-contrib-9.5 
                        
      To Install pgRouting 2.1 package:         
      > $ sudo apt-get install postgresql-9.5-pgrouting         
                  
* after PostGIS is installed create database and then put this db name in your settings.py file:             
      > $ createdb  <db name>          
      > $ psql <db name>        
      > $ > CREATE EXTENSION postgis;    
                  
* copy the Ashbourn/settings.py.sample file into Ashbourn/settings.py and modify as needed for your own computer and database
      
* Then run this command to install all requirements         
      > $ pip install -r requirements.txt   
            
* Then run this command to create the models in the db        
      > $ python manage.py migrate --run-syncdb   
            
Alexandr Folder is separate project code being considered being encorporated into the Ashbourn project
