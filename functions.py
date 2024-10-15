import geopandas as gp
import OSGridConverter as converter
import shapely.geometry as geo
import h3
import collections 
from shapely.ops import substring
import math

def clip_study_area(data,centre_coord,distance):

    #data: target geodataframe to clip
    #centre_coord: coordinates (array) of centre point of the desired area
    #distance: clipping radius in meters

    centre_BNG=converter.latlong2grid(centre_coord[0],centre_coord[1])
    centre_point=gp.GeoSeries([geo.Point([centre_BNG.E],[centre_BNG.N])],crs="EPSG:27700")
    clip_mask=centre_point.buffer(distance)
    clipped_area=gp.clip(data,clip_mask.geometry[0],keep_geom_type=True)
    return clipped_area

def create_grid(centre_coord,resolution,size):

    #centre_coord: central point coordinates to create the grid
    #resolution: size of hex cell
    #size: radius of the grid

    centre_cell=h3.latlng_to_cell(centre_coord[0],centre_coord[1],resolution)
    hexgrid=h3.grid_disk(centre_cell,k=size)
    BNGlist=[]
    for cell in hexgrid:
        lat,lng=h3.cell_to_latlng(cell)
        BNG=converter.latlong2grid(lat,lng)
        BNGlist.append(BNG)
    gridgeometry=gp.GeoSeries([geo.Point(BNG.E,BNG.N) for BNG in BNGlist])
    geogrid=gp.GeoDataFrame({"gridid":range(0,len(gridgeometry))},geometry=gridgeometry,crs="EPSG:27700")
    return geogrid

def road_split(roadnetwork,resolution):

    #roadnetwork: target geodataframe to split 
    #resolution: length interval when splitting

    segmented_list=[]
    for roadline in roadnetwork.geometry:
        if roadline.length<resolution:
            segmented_list.append(roadline)
        else:
            seg_count=math.floor(roadline.length/resolution)
            for count in range(1,(seg_count+1)):
                if (roadline.length-resolution*count)>resolution:
                    segmented_list.append(substring(roadline,resolution*(count-1),resolution*count))
                else:
                    segmented_list.append(substring(roadline,resolution*(count-1),resolution*count))
                    segmented_list.append(substring(roadline,resolution*count,roadline.length))
    segmented_road=gp.GeoSeries(segmented_list,crs="EPSG:27700")
    return segmented_road

def knearest(target_point,sampling_point,k,d):

    #target_point: target geodataframe to classify
    #sampling_point: input geodataframe to train
    #k: number of the nearest neighbours

    target_point=target_point.assign(risk='NaN')
    for frompoint in target_point.geometry:
        regional=sampling_point.cx[(frompoint.x-d):(frompoint.x+d),(frompoint.y-d):(frompoint.y+d)]
        regional["dist"]=[topoint.distance(frompoint) for topoint in regional.geometry]
        regional.sort_values(by='dist',ascending=True,inplace=True)
        match_index=list(regional["gridid_1"])[:k]
        risklist=[regional.loc[regional['gridid_1']==index,['prob_4band']]for index in match_index]
        risklist=[risklist[x].values.tolist() for x in range(0,k)]
        risklist=[x for xss in risklist for xs in xss for x in xs]
        counter=collections.Counter(risklist)
        risk=counter.most_common(1)
        target_point.loc[target_point['geometry']==frompoint,["risk"]]=risk[0][0]
    return target_point

def level_to_value(risklevel):

    #risklevel: risk category

    if risklevel=='High':
        return 4
    elif risklevel=='Medium':
        return 3
    elif risklevel=='Low':
        return 2
    elif risklevel=='Very Low':
        return 1
    else:
        return 0


