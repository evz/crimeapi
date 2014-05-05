import requests
from globalmaptiles import GlobalMercator
from tilenames import tileXY, tileEdges
from operator import itemgetter
from itertools import groupby
import cv2
import numpy as np
import cairo
import os
from helpers import dl_write_all, hex_to_rgb, get_pixel_coords
from datetime import datetime
from shapely.geometry import box, Polygon, MultiPolygon, Point

mercator = GlobalMercator()

PAGE_SIZES = {
    'letter': (1275,1650,5,7,),
    'tabloid': (2550,3300,10,14,),
}

def pdfer(data, page_size='letter'):
    overlays = data.get('overlays')
    grid = {'zoom': data.get('zoom')}
    center_lon, center_lat = data['center']
    center_tile_x, center_tile_y = tileXY(float(center_lat), float(center_lon), int(data['zoom']))
    dim_across, dim_up = data['dimensions']
    if dim_across > dim_up:
        page_height, page_width, tiles_up, tiles_across = PAGE_SIZES[page_size]
        orientation = 'landscape'
    else:
        page_width, page_height, tiles_across, tiles_up = PAGE_SIZES[page_size]
        orientation = 'portrait'
    min_tile_x = center_tile_x - (tiles_across / 2)
    min_tile_y = center_tile_y - (tiles_up / 2)
    max_tile_x = min_tile_x + tiles_across
    max_tile_y = min_tile_y + tiles_up
    links = []
    for ty in range(min_tile_y, max_tile_y + 1):
        for tx in range(min_tile_x, max_tile_x + 1):
            links.append('http://a.tiles.mapbox.com/v3/datamade.hnmob3j3/{0}/{1}/{2}.png'.format(grid['zoom'], tx, ty))
    names = dl_write_all(links)
    now = datetime.now()
    date_string = datetime.strftime(now, '%Y-%m-%d_%H-%M-%S')
    outp_name = os.path.join('/tmp', '{0}.png'.format(date_string))
    image_names = ['-'.join(l.split('/')[-3:]) for l in names]
    image_names = sorted([i.split('-') for i in image_names])
    arrays = []
    for k,g in groupby(image_names, key=itemgetter(4)):
        images = list(g)
        fnames = ['/tmp/%s' % ('-'.join(f)) for f in images]
        array = []
        for img in fnames:
            array.append(cv2.imread(img))
        arrays.append(np.vstack(array))
    outp = np.hstack(arrays)
    cv2.imwrite(outp_name, outp)
    for parts in image_names:
        parts = parts[3:]
        parts[-1] = parts[-1].rstrip('.png')
        key = '-'.join(parts[-3:])
        grid[key] = {'bbox': tileEdges(float(parts[1]),float(parts[2]),int(parts[0]))}
    d = {}
    keys = sorted(grid.keys())
    if overlays:
        polys = []
        for k,v in grid.items():
            try:
                one,two,three,four = grid[k]['bbox']
                polys.append(box(two, one, four, three))
            except TypeError:
                pass
        mpoly = MultiPolygon(polys)
        bb_poly = box(*mpoly.bounds)
        min_key = keys[0]
        max_key = keys[-2]
        bminx, bminy = grid[min_key]['bbox'][0], grid[min_key]['bbox'][1]
        bmaxx, bmaxy = grid[max_key]['bbox'][2], grid[max_key]['bbox'][3]
        bmin_mx, bmin_my = mercator.LatLonToMeters(bminx, bminy)
        bmax_mx, bmax_my = mercator.LatLonToMeters(bmaxx, bmaxy)
        bmin_px, bmin_py = mercator.MetersToPixels(bmin_mx,bmin_my,float(grid['zoom']))
        bmax_px, bmax_py = mercator.MetersToPixels(bmax_mx,bmax_my,float(grid['zoom']))
        bmin_rx, bmin_ry = mercator.PixelsToRaster(bmin_px,bmin_py,int(grid['zoom']))
        im = cairo.ImageSurface.create_from_png(outp_name)
        ctx = cairo.Context(im)
        for beat_overlay in overlays.get('beat_overlays'):
            color = hex_to_rgb('#7B3294')
            boundary = requests.get('http://crimearound.us/data/beats/%s.geojson' % beat_overlay)
            if boundary.status_code == 200:
                coords = boundary.json()['coordinates'][0]
                x, y = get_pixel_coords(coords[0], grid['zoom'], bmin_rx, bmin_ry)
                ctx.move_to(x,y)
                ctx.set_line_width(4.0)
                for p in coords[1:]:
                    x, y = get_pixel_coords(p, grid['zoom'], bmin_rx, bmin_ry)
                    red, green, blue = [float(c) for c in color]
                    ctx.set_source_rgba(red/255, green/255, blue/255, 0.7)
                    ctx.line_to(x,y)
                ctx.close_path()
                ctx.stroke()
        if overlays.get('shape_overlay'):
            shape_overlay = overlays['shape_overlay']
            color = hex_to_rgb('#f06eaa')
            coords = shape_overlay['coordinates'][0]
            x, y = get_pixel_coords(coords[0], grid['zoom'], bmin_rx, bmin_ry)
            ctx.move_to(x,y)
            ctx.set_line_width(4.0)
            red, green, blue = [float(c) for c in color]
            ctx.set_source_rgba(red/255, green/255, blue/255, 0.3)
            for p in coords[1:]:
                x, y = get_pixel_coords(p, grid['zoom'], bmin_rx, bmin_ry)
                ctx.line_to(x,y)
            ctx.close_path()
            ctx.fill()
            ctx.set_source_rgba(red/255, green/255, blue/255, 0.5)
            for p in coords[1:]:
                x, y = get_pixel_coords(p, grid['zoom'], bmin_rx, bmin_ry)
                ctx.line_to(x,y)
            ctx.close_path()
            ctx.stroke()
        ctx.set_line_width(3.0)
        for point_overlay in overlays.get('point_overlays'):
            color = hex_to_rgb(point_overlay['color'])
            for p in point_overlay['points']:
                pt = Point((float(p[0]), float(p[1])))
                if bb_poly.contains(pt):
                    nx, ny = get_pixel_coords(p, grid['zoom'], bmin_rx, bmin_ry)
                    red, green, blue = [float(c) for c in color]
                    ctx.set_source_rgba(red/255, green/255, blue/255, 0.6)
                    ctx.arc(nx, ny, 10.0, 0, 50) # args: center-x, center-y, radius, ?, ?
                    ctx.fill()
                    ctx.arc(nx, ny, 10.0, 0, 50)
                    ctx.stroke()
        im.write_to_png(outp_name)
    scale = 1
    pdf_name = outp_name.rstrip('.png') + '.pdf'
    pdf = cairo.PDFSurface(pdf_name, page_width, page_height)
    ctx = cairo.Context(pdf)
    image = cairo.ImageSurface.create_from_png(outp_name)
    ctx.set_source_surface(image, 0, 0)
    ctx.paint()
    pdf.finish()
    return pdf_name

if __name__ == "__main__":
    data = {'center': [-87.65137195587158, 41.8737151810189],
        'dimensions': [890, 600],
        'overlays':{
             'point_overlays': [{'color': '#ff0000',
                 'points': [[-87.6426826613853, 41.8781071880535],
                     [-87.63938375754306, 41.867041706472456],
                     [-87.6545186129677, 41.865850595857054],
                     [-87.63909667701795, 41.86880452372822],
                     [-87.6393048378162, 41.86449456528135],
                     [-87.6393679750852, 41.867143148345015],
                     [-87.64741565794833, 41.87881063893845],
                     [-87.65197660167782, 41.87670825544318],
                     [-87.63909667701795, 41.86880452372822],
                     [-87.65620174057511, 41.86603890823199],
                     [-87.65714742488014, 41.866878732430045],
                     [-87.66390400959368, 41.86815871640521],
                     [-87.65196361130707, 41.874474361734165],
                     [-87.63909667701795, 41.86880452372822],
                     [-87.65696499902725, 41.874432576058304],
                     [-87.65685596043203, 41.876416024306245],
                     [-87.64395748847578, 41.87189638577255],
                     [-87.6548116345001, 41.8777184577741],
                     [-87.65934485800273, 41.86599153498752],
                     [-87.65924273143733, 41.86592781781541]]}],
            'beat_overlays': ['0124'],
            'shape_overlays': [],
        },
        'zoom': 15}
    print pdfer(data, page_size='tabloid')
