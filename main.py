import hashlib
from urllib import parse
import webcolors
from PIL import Image
import os

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.response import FileResponse
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

import time
import json

def defaultAccess(spot,key,default=""):
    try:
        value = spot.attrs[key]
    except KeyError as r:
        value = default
    return value

class spot:
    def __init__(self,query_string):
        self.query_string = query_string
        self.attrs = dict(parse.parse_qsl(query_string))
        self.x = self.attrs['x']
        self.y = self.attrs['y']
        self.color = self.attrs['color']
        self.hash = hashlib.sha256(self.query_string.encode()).hexdigest()
    def info(self):
        return f"<div id = 'query_string'>{self.query_string}</div><div id = 'hash'>{self.hash}</div>"
    def pageView(self):
        title = defaultAccess(self,"title")
        text = defaultAccess(self,"text")
        color = defaultAccess(self,"color")
        href = defaultAccess(self,"href")
        image = defaultAccess(self,"image")
        style = """<style>
    ul {padding:0px; margin: 0px;
        display:in-line-block;
    }
    li {
        display: inline-block;
       }
</style>"""
        bar = f"<div style = 'background-color:{self.color}'><br></div>"
        img = f"<img id='image' src='data:image/png;base64,{image}' />"
        return f"""
{style}{bar}
<ul>
    <li><h2 id = 'title'>{title}</h2></li>
    <li style = 'float: right;'><br> {img if len(image) else ""} </li>
</ul>
<ul>
    <li><h5>x:</h5></li><li><h5 id = 'x'>{self.x}</h5></li>
    <li><h5>y:</h5></li><li><h5 id = 'y'>{self.y}</h5></li>
    <li><h5>color:</h5></li><li><h5 id = 'color'>{self.color}</h5></li>
</ul>
<div>
    <p id = 'text'>{text}</p>
</div><br>
{f"<div><a id = 'link' href = {href}>{href}</a></div><br>" if len(href) else ""}
{bar}<br>
{self.info()}"""

def processColor(c):
    try:
        color = tuple(webcolors.name_to_rgb(c))
    except ValueError as e:
        try:
            color = tuple(webcolors.hex_to_rgb(c))
        except ValueError as e:
            return False
    return color


class board:
    size = 421
    styles = ""
    canvasStuff = ""
    def __init__(self):
        self.data = []
        self.img = Image.new(mode="RGB", size=(board.size, board.size))
        try:
            with open("data.json","r") as f:
                self.data = [[spot(q) for q in row] for row in json.load(f)]
            for x in range(board.size):
                for y in range(board.size):
                    self.img.putpixel((x,y), processColor(self.data[x][y].color))
        except (FileNotFoundError, json.decoder.JSONDecodeError):                
            for x in range(board.size):
                row = []
                for y in range(board.size):
                    row.append(spot(f'x={x}&y={y}&color=tomato'))
                    self.img.putpixel((x,y), processColor('tomato'))
                self.data.append(row)
        self.lastSave = time.time()
        self.deltaCount = 0
        self.upkeep(force=True)
        self.templates()
    def upkeep(self,force=False):
        if force or (self.deltaCount >= 420 or (time.time()-self.lastSave > 69 and self.deltaCount)):
            self.saveImg()
            self.saveJson()
            self.lastSave = time.time()
            self.deltaCount = 0
    def saveJson(self):
        with open("data.json","w") as f:
            json.dump([[q.query_string for q in row] for row in self.data],f)
    def templates(self):
        board.styles = """
<style>

</style>
"""
        board.canvasStuff = """

<canvas id = canvas></canvas>

<script>
    var canvas = document.getElementById("canvas");
    ctx = canvas.getContext("2d");

    canvas.width = """+str(board.size)+""";
    canvas.height = """+str(board.size)+""";

    var background = new Image();
    background.src = "home.png";

    background.onload = function(){
        ctx.drawImage(background,0,0);   
    }
    
    setInterval(() => {
        var background = new Image();
        background.src = "home.png?roll="+new Date().getTime();
        document.getElementById("canvas").canvas.getContext("2d").drawImage(background,0,0);
        console.log("Check 1,2");
    }, 1000*15);
    
    canvas.addEventListener('click', function(e) {
        var x;
        var y;
        if (e.pageX || e.pageY) { 
          x = e.pageX;
          y = e.pageY;
        }
        else { 
          x = e.clientX + document.body.scrollLeft + document.documentElement.scrollLeft; 
          y = e.clientY + document.body.scrollTop + document.documentElement.scrollTop; 
        } 
        x -= canvas.offsetLeft;
        y -= canvas.offsetTop;
        window.location.href = './?x='+x+'&y='+y;     
    }, false);
    
    
    
</script>
"""
    def saveImg(self):
        self.img.save("home.png")
    def updateSpot(self,x,y):
        c = processColor(self.data[x][y].attrs['color'])
        self.img.putpixel((x,y), processColor(self.data[x][y].color))
        self.deltaCount+=1
        self.upkeep()
    def pixelView(self):
        self.upkeep()
        return board.styles + board.canvasStuff


@view_config(route_name='png')
def serve_png(request):
    response = FileResponse(
        './home.png',
        request=request,
        content_type='image/png'
        )
    return response


@view_config(route_name='json')
def serve_json(request):
    response = FileResponse(
        './data.json',
        request=request,
        content_type='text/json'
        )
    return response


def hashCheck(hash,threshold):
    return int(hash,16) < int(threshold,16)
    
place = board()
def over_view(request):
    data = dict(parse.parse_qsl(request.query_string))
    if 'x' in data.keys() and 'y' in data.keys():
        x = int(data['x'])
        y = int(data['y'])
        if request.query_string == place.data[x][y].query_string:
            return Response(content_type="text/html",body=place.data[x][y].pageView())
        if x>=0 and x<place.size and y>=0 and y<place.size:
            if 'color' in data.keys() and hashCheck(hashlib.sha256(request.query_string.encode()).hexdigest(),place.data[x][y].hash):
                if processColor(data['color']):
                    place.data[x][y] = spot(request.query_string)
                    place.updateSpot(x,y)
            return HTTPFound(location=f'./?{place.data[x][y].query_string}')
            #return Response(content_type="text/html",body=f"""<script>window.location.href = './?{place.data[x][y].query_string}';</script>""")
    return Response(content_type="text/html",body=place.pixelView())

if __name__ == '__main__':
    with Configurator() as config:
        config.add_route('top', r'/')
        config.add_view(over_view, route_name='top')
        config.add_route('png', '/home.png')
        config.add_route('json', '/data.json')
        config.scan('__main__')
        app = config.make_wsgi_app()
    try:
        port = int(os.environ['PORT'])
    except KeyError:
        port = 6450
    server = make_server('0.0.0.0', port , app)
    server.serve_forever()

