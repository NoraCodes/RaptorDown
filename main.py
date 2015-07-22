#! /bin/python2.7
"""

A LibTCOD roguelike... in SPAES!

By Leo Tindall

Based on http://www.roguebasin.com/index.php?title=Complete_Roguelike_Tutorial,_using_python%2Blibtcod

"""

#TODO: Objects show as holes in the floor

import libtcodpy as libtcod
import math #For rounding UI positions and map building
import time #For frame timings
import textwrap #For log wrapping

#Setup
#--UI Elements
#---Global
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
CONSOLE_TITLE = "Raptor Down"
CONSOLE_FULLSCREEN = False
LIMIT_FPS = 20
DEBUG = True
#----Map Console
MCON_WIDTH = int(round(SCREEN_WIDTH * 0.75))
MCON_HEIGHT = int(round(SCREEN_HEIGHT * 0.75))
MCON_DRAW_OFFSET_X = 1 #How far from the left border to draw the map
MCON_DRAW_OFFSET_Y = 1 #how far from the top border to draw the map

PCON_WIDTH = int(round(SCREEN_WIDTH * 0.25) - 1)
PCON_HEIGHT = MCON_HEIGHT + 1

CCON_WIDTH = SCREEN_WIDTH - 2
CCON_HEIGHT = 9



RCON = 0 # The root console
MCON = libtcod.console_new(MCON_WIDTH, MCON_HEIGHT) #The console to draw maps onto
PCON = libtcod.console_new(PCON_WIDTH, PCON_HEIGHT) #The console to draw the GUI onto
CCON = libtcod.console_new(CCON_WIDTH, CCON_HEIGHT) #The console to draw the log onto

#--Game Elements
#----Map Constraints
MAP_HEIGHT = MCON_HEIGHT #TODO: Implement scrolling so that these are no longer coupled
MAP_WIDTH = MCON_WIDTH

MAP_DECAY_RATE = 10 #Percent chance that exposed tiles decay
MAP_DECAY_PASSES = 15 #Decay loop how many times? Probably should be at least 2.

ROOM_MAX_SIZE = MAP_WIDTH / 5
ROOM_MIN_SIZE = MAP_WIDTH / 10
MAX_ROOMS = 50 #How many rooms should we try to generate?

ROOM_MAX_MONSTERS = 3
ROOM_MAX_ITEMS = 3
MONSTER_SPAWN_CHANCE = 80 #Percent; higher = harder
ITEM_SPAWN_CHANCE = 30 #Percent; lower = harder
DROP_BUFF_CHANCE = 100 #Percent; can be lowered to vastly increase difficulty
DROP_HEAL_CHANCE = 10
DROP_MHP_CHANCE = 10
DROP_ATK_CHANCE = 25
DROP_DEF_CHANCE = 25
DROP_LIGHT_CHANCE = 5


MONSTER_TYPES = [
    {"id" : 0, "name" : "Glorp", "description" : "A blob of goo, which Colonials call Glorp. It's a semi-sentient collection of tylium.", "char" : "g", "color" : libtcod.green, "hp" : 10, "atk" : 1, "def" : 1, "speed" : 1, "ai_type": "passive"},
    {"id" : 1, "name" : "Scout", "description" : "A Cylon scout, a small 8-legged creature with a camera onboard.", "char" : "s", "color" : libtcod.light_gray, "hp" : 1, "atk" : 0, "def" : 1, "speed" : 1, "ai_type": "nonsensical"},
    {"id" : 2, "name" : "Combat Scout", "description" : "A Cylon scout, outfitted for combat.", "char" : "c", "color" : libtcod.gray, 
"hp" : 2, "atk" : 1, "def" : 1, "speed" : 1, "ai_type": "aggressive"}
]

MONSTER_TYPES_NOAUTO = [
    {"id" : 200, "name" : "Centurion", "description" : "A huge metal Cylon armed with sharp claws. The perfect killing machine.", "char" : "C", "color" : libtcod.darker_red, "hp" : 50, "atk" : 10, "def" : 10, "speed" : 1, "ai_type": "aggressive"},
    {"id" : 201, "name" : "Six", "description" : "A beautiful Cylon woman armed with a short vibraknife.", "char" : "6", "color" : libtcod.red, "hp" : 1, "atk" : 3, "def" : 3, "speed" : 1, "ai_type": "aggressive"},
    {"id" : 202, "name" : "Three", "description" : "A short Cylon woman, holding a rather terrifying katana.", "char" : "3", "color" : libtcod.red, "hp" : 30, "atk" : 5, "def" : 3, "speed" : 1, "ai_type": "aggressive"}
]

COUNTDOWN_MAX = 150

#----FOV

FOV_ALGO = 0  #default FOV algorithm
FOV_LIGHT_WALLS = True



#--Colors

color_zero = libtcod.Color(0,0,0)
color_blank = libtcod.Color(25,25,25)
color_ui_health = libtcod.Color(15,250,15)
color_ui_fuel = libtcod.Color(250,250,15)
color_ui_charge = libtcod.Color(15,15,250)
color_ui_countdown = libtcod.Color(250,15,15)
color_ui_text = libtcod.Color(150,150,150)

color_dark_wall = libtcod.Color(100,100,100)
color_light_wall = libtcod.Color(200,200,200)
color_dark_bg = libtcod.Color(30,30,30)
color_light_bg = libtcod.Color(50,50,50)

def debug(message):
    """
    Send a message to the console if debug mode is on
    :param message: The message to be printed.
    :return:Nothing
    """
    if DEBUG is True:
        print "[D]  " + message


#Classes
class Rect:
    """A rectangle, for defining rooms."""
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h
    def center(self):
        """Find the center of a Rect"""
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)

    def intersect(self, other):
        """Does this Rect intersect with other?"""
        #returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

class World:
    """A world containing objects."""
    def __init__(self):
        self.Map = None #The map for placing things on
        self.FOVMap = None #The map overlay for calculating
        self.mapheight = MAP_HEIGHT
        self.mapwidth = MAP_WIDTH
        self.Objects = []
        self.player = None
        self.player_spawn_x = 0
        self.player_spawn_y = 0
        self.spawn_x = 0
        self.spawn_y = 0
        self.countdown = COUNTDOWN_MAX + 1
        self.donecount = False #Has the countdown finished already?
        self.build_map()
        self.build_fovmap()

    def spawn_object(self, obj):
        """Add an object to the world."""
        debug("Adding an object \"" + obj.name + "\" to the world at X:" + str(obj.x) + " Y: " + str(obj.y) + ".")
        if not obj.world is None: #Spawning makes this false. Here we are checking to make sure that the object does not already exist somewhere, as that would introduce a lot of really weird bugs.
            debug("We can't spawn an \"" + obj.name + "\", it's already spawned somewhere. Despawn it there first.")
        status, object_hit = self.is_blocked(obj.x, obj.y)
        if status == 1:
            debug("\tWe can't spawn an \"" + obj.name + "\" because it's in the wall.")
            return False
        elif status == 2:
            debug("\tWe can't spawn an \"" + obj.name + "\" because it's in an\"" + object_hit.name + "\"")
        else:
            obj.world = self
            self.Objects.append(obj)
            return True

    def despawn_object(self, obj):
        """Remove an object from the world."""
        if obj.world is None:
            debug("Despawning an unspawned object \"" + obj.name + "\".")
        debug("Removed an \"" + obj.name + "\" from the world.")
        self.Objects.remove(obj)

    def spawn_player(self, obj):
        """Set an object as the player."""
        debug("Spawning the player.")
        self.player = obj
        self.player.x = self.player_spawn_x
        self.player.y = self.player_spawn_y
        debug("\tSpawned the player at X:" + str(self.player_spawn_x) + " Y:" + str(self.player_spawn_y))

    def despawn_player(self):
        """Remove the player."""
        debug("Despawned the player.")
        self.player = None

    def create_room(self, room, world):
        """Turn a Rect into a room on the map in world."""
        #Check to make sure we're not off the map. That would be bad.
        if (room.x1 < 0) or (room.x2 >= world.mapwidth) or (room.y1 < 0) or (room.y2 >= world.mapheight):
            raise KeyError("Tried to build a room off the map!")
        for x in range(room.x1 + 1, room.x2): #Leaving out one tile from the left by adding one, and one from the right by just using range
            for y in range(room.y1+1, room.y2): #Leaving out one tile from the top by adding one, and one from the bottom by just using range
                self.Map[x][y].unblock()

    def create_h_tunnel(self, x1, x2, y, world):
        """Make a tunnel between x1 and x2 at y on the map in world."""
        for x in range(min(x1, x2) + 1, max(x1, x2)):
            self.Map[x][y].unblock()

    def create_v_tunnel(self, y1, y2, x, world):
        """Make a tunnel between y1 and y2 at x on the map in world."""
        for y in range(min(y1, y2) + 1, max(y1, y2)):
            self.Map[x][y].unblock()

    def is_blocked(self, x ,y):
        if self.Map[x][y].blocked:
            return (1, None)

        for obj in self.Objects:
            if obj.blocks and obj.x == x and obj.y == y:
                return (2, obj)
        if self.player: #This section would cause a crash if the player didn't exist
            if  x == self.player.x and y == self.player.y:
                return (2, self.player)

        return (0, None)

    def build_map(self):
        """Build a map in our Map variable."""
        #Fill the map in with blocked tiles
        debug("Building a map in the world.")
        self.Map = [[ Tile(True)
                for y in range(self.mapheight)]
                    for x in range(self.mapwidth)]

        #Here we make rooms and connect them with tunnels
        debug("\tDone wiping map, building rooms...")
        rooms = []
        num_rooms = 0
        for room in range(MAX_ROOMS):
            #pick a random width and height
            w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE) #Get a random width for the room
            h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE) #Get a random height for the room
            #Random position in the world
            x = libtcod.random_get_int(0,1,self.mapwidth - w - 2) #Minimum of one and maximum of 1 less than the actual maximum element to preserve a border around the world
            y = libtcod.random_get_int(0,1,self.mapheight - h - 2)
            #Now, actually create, check, and map the room
            new_room = Rect(x,y,w,h)
            failed = False #Have we failed this room for some reason?
            for other_room in rooms:
                if new_room.intersect(other_room):
                    failed = True
                    break
            if not failed: #If the room is valid, spawn it on to the real map
                self.create_room(new_room, self)
                #Grab the center coords
                (new_room_center_x, new_room_center_y) = new_room.center()
                if num_rooms == 0:
                    #This is the first room, so move the player here
                    self.player_spawn_x = new_room_center_x
                    self.player_spawn_y = new_room_center_y
                    debug("\tPlayer spawn set to (" + str(self.player_spawn_x) + "," + str(self.player_spawn_y) + ").")
                else:
                    #This is not the first room, so it needs connected to the other rooms
                    previous_room = rooms[num_rooms - 1]
                    (previous_room_center_x, previous_room_center_y) = rooms[num_rooms - 1].center()
                    #Randomly decide how to try building tunnels; hor/vert or vert/hor
                    if libtcod.random_get_int(0,0,1) == 1:
                        self.create_h_tunnel(previous_room_center_x, new_room_center_x, previous_room_center_y, self)
                        self.create_v_tunnel(previous_room_center_y, new_room_center_y, new_room_center_x, self)
                    else:
                       self.create_v_tunnel(previous_room_center_y, new_room_center_y, previous_room_center_x, self)
                       self.create_h_tunnel(previous_room_center_x , new_room_center_x, new_room_center_y, self)
                rooms.append(new_room) #Add the room to the list
                self.place_objects(new_room) #Add NPCs and items to the room
                num_rooms += 1 #We've successfully added a room, so add one to the number of rooms.
        debug("\tDone building rooms.")
        for n in range(MAP_DECAY_PASSES):
            debug("\tDecay pass " + str(n + 1) + " of " + str(MAP_DECAY_PASSES))
            #Now, we'll "decay" the map a little. This means: removing tiles which have 2 sides exposed.
            for y in range(1, self.mapheight - 2):
                for x in range(1, self.mapheight - 2):
                    sides_exposed = 0 # How many faces of this block are exposed?
                    if not self.Map[x - 1][y].blocked:
                        #Left side
                        sides_exposed += 1
                    if not self.Map[x + 1][y].blocked:
                        #Right side
                        sides_exposed += 1
                    if not self.Map[x][y - 1].blocked:
                        #Top side
                        sides_exposed += 1
                    if not self.Map[x][y + 1].blocked:
                        #Bottom side
                        sides_exposed += 1
                    #Now, we know how many sides are exposed.
                    if sides_exposed == 1:
                        #Maybe decay this, based on MAP_DECAY_RATE
                        if libtcod.random_get_int(0, 0, 100) < MAP_DECAY_RATE: #This gives a MAP_DECAY_RATE percent chance.
                            self.Map[x][y].unblock()
                    if sides_exposed > 2:
                        #This might be blocking a path so we need to decay it
                        self.Map[x][y].unblock()

    def build_fovmap(self):
        """Build the FOVMap from the Map. Probably should be called after building the map or FOV won't work."""
        self.FOVMap = libtcod.map_new(self.mapwidth, self.mapheight) #A blank map
        for y in range(self.mapheight):
            for x in range(self.mapwidth):
                libtcod.map_set_properties(self.FOVMap, x, y, not self.Map[x][y].block_sight, not self.Map[x][y].blocked)

    def place_objects(self, room):
        """
        Place objects in the room.
        :param room: The room on which to operate.
        :return:
        """
        num_monsters = libtcod.random_get_int(0,0,ROOM_MAX_MONSTERS)
        num_items = libtcod.random_get_int(0,0,ROOM_MAX_ITEMS) #TODO: Acually spawn items

        for i in range(num_items):
            x = libtcod.random_get_int(0, room.x1, room.x2)
            y = libtcod.random_get_int(0, room.y1, room.y2)

            if libtcod.random_get_int(0, 0, 100) <= ITEM_SPAWN_CHANCE:
                new_monster = GameItem(x, y, "f", libtcod.yellow, name = "Fuel", description="A big lump of Tylium, a very powerful fuel.", fuel = libtcod.random_get_int(0,10,25))
                self.spawn_object(new_monster) # Actually place the monster into the world

        for i in range(num_monsters):
            x = libtcod.random_get_int(0, room.x1, room.x2)
            y = libtcod.random_get_int(0, room.y1, room.y2)

            if libtcod.random_get_int(0, 0, 100) <= MONSTER_SPAWN_CHANCE:
                new_monster_properties = MONSTER_TYPES[libtcod.random_get_int(0, 0, len(MONSTER_TYPES) - 1)] #Pick a monster type.
                new_monster = GameNPC(x, y, new_monster_properties["char"], new_monster_properties["color"], new_monster_properties["speed"], new_monster_properties["hp"], new_monster_properties["atk"], new_monster_properties["def"], new_monster_properties["name"], new_monster_properties["description"], new_monster_properties["ai_type"])
                self.spawn_object(new_monster) # Actually place the monster into the world

    def update(self):
        """Run AI for all the objects in our world."""
        for object in self.Objects:
            object.update(self)
        self.player.update(self)
        if self.countdown > 0:
            self.countdown -= 1
        #If the timer is over, spawn enemies in huge quantities
        if self.countdown <= 0:
            if self.donecount == False: #First time
                self.donecount = True
                message("The Cylons have begun jumping in! You are about to be swarmed!", libtcod.red)
            target_is_free = 1
            self.spawn_x = 0
            self.spawn_y = 0
            while not target_is_free == 0: #Pick random locations until we have one
                self.spawn_x = libtcod.random_get_int(0,0,MAP_WIDTH - 1)
                self.spawn_y = libtcod.random_get_int(0,0,MAP_HEIGHT - 1)
                (target_is_free, object) = world.is_blocked(self.spawn_x,self.spawn_y)
                new_monster_properties = MONSTER_TYPES_NOAUTO[libtcod.random_get_int(0, 0, len(MONSTER_TYPES_NOAUTO) - 1)] #Pick a monster type.
                new_monster = GameNPC(self.spawn_x, self.spawn_y, new_monster_properties["char"], new_monster_properties["color"], new_monster_properties["speed"], new_monster_properties["hp"], new_monster_properties["atk"], new_monster_properties["def"], new_monster_properties["name"], new_monster_properties["description"], new_monster_properties["ai_type"])
                self.spawn_object(new_monster) # Actually place the monster into the world

    def draw(self, console):
        """Draw the world."""
        self.clear(console)
        self.clear_map(console)
        #Draw the map)
        for y in range(self.mapheight - 1):
            for x in range(self.mapwidth - 1):
                current_tile_is_visible = libtcod.map_is_in_fov(self.FOVMap, x, y)
                current_tile_is_explored = self.Map[x][y].explored
                current_tile_is_wall = self.Map[x][y].block_sight
                if not current_tile_is_visible: #If we're rendering a tile we can't see
                    if current_tile_is_explored:#The player can only see it if it's explored
                        if current_tile_is_wall:#And in that case use dark colors
                            libtcod.console_put_char_ex(console, x, y, '#', color_dark_wall, color_dark_bg)
                        else:
                            libtcod.console_put_char_ex(console, x, y, '.', color_dark_wall, color_dark_bg)
                else: #If we're rendering a tile we can see, use light colors. Also, mark the tile as explored.
                    if current_tile_is_wall:
                         #libtcod.console_set_char_background(console, x, y, color_dark_wall, libtcod.BKGND_SET)
                        libtcod.console_put_char_ex(console, x, y, '#', color_light_wall, color_light_bg)
                    else:
                        libtcod.console_put_char_ex(console, x, y, '.', color_light_wall, color_light_bg)
        #Draw objects and the player
        for object in self.Objects:
            object.draw(console)
        self.player.draw(console)

    def clear(self, console):
        """Clear the graphics for objects in the world."""
        for object in self.Objects:
            object.clear(console)
        self.player.clear(console)

    def clear_map(self, console):
        """Clear the map from the screen."""
        #Clear the map
        for y in range(self.mapheight):
            for x in range(self.mapwidth):
                libtcod.console_put_char_ex(console, x, y, ' ', color_blank, color_blank)

class GameObject(object):
    """A generic object. Represents a player, item, enemy, etc. 1 object = 1 character on screen"""
    def __init__(self, x, y, char, color, name="Perfectly Generic Object", description="A perfectly generic object."):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.description = description
        self.name = name
        self.visible = False
        self.blocks = True
        self.world = None

    def interact(self, interlocutor):
        message(self.describe(), color_ui_text)

    def move_towards(self, target_x, target_y, world):
        debug(self.name + " is moving towards x:" + str(target_x) + " Y:" + str(target_y))
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
        #Normalize to length one, then move.
        try:
            dx = int(round(dx / distance))
            dy = int(round(dy / distance))
        except ZeroDivisionError, e:
            return True#This is ok - we're right on top of 'em!
        self.move(dx,dy, world)
        return False

    def move_away(self, target_x, target_y, world):
        debug(self.name + " is moving away from x:" + str(target_x) + " Y:" + str(target_y))
        dx = 0 - ( target_x )
        dy = 0 - ( target_y )
        self.move_towards(dx, dy, world)

    def move(self, dx, dy, world):
        """Move (dx,dy) from the current position, checking for collisions in world and out-of-bounding in world."""
        if (self.x + dx < 0) or (self.x + dx >= world.mapwidth) or (self.y + dy < 0) or (self.y + dy >= world.mapheight):
            debug("Object \"" + self.name + "\" hit the edge of the map.")
        else:
            (block_status, object_hit) = world.is_blocked(self.x + dx, self.y + dy) #Check for collisions to map tiles
            if block_status == 1:
                debug("Object \"" + self.name + "\" hit a wall.")
            elif block_status == 2:
                debug("Object \"" + self.name + "\" hit another object (" + object_hit.name + ").")
                object_hit.interact(self)
            else: #If we reach here, we are OK to move.
                self.x += dx
                self.y += dy

    def distance(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx **2 + dy ** 2)

    def update(self, world):
        """Do AI for the object."""
        self.visible = libtcod.map_is_in_fov(world.FOVMap, self.x, self.y)

    def draw(self, console):
        """Set the color to draw with, then draw this object at the appropriate location, only if visible."""
        if self.visible:
            libtcod.console_set_default_foreground(console, self.color)
            libtcod.console_put_char(console, self.x, self.y, self.char, libtcod.BKGND_NONE)

    def clear(self, console):
        """Remove the graphic that represents this object."""
        libtcod.console_put_char(console, self.x, self.y, ' ', libtcod.BKGND_NONE)

    def describe(self):
        """Return the description of the object."""
        return self.description

class GameItem(GameObject):
    def __init__(self, x, y, char, color, buff_atk = 0, buff_def = 0, buff_heal = 0, buff_light = 0, fuel = 0, hp = 0, name="Perfectly Generic Object", description="A perfectly generic object."):
        super(GameItem, self).__init__(x,y,char,color,name,description)
        self.buff_atk = buff_atk
        self.buff_def = buff_def
        self.buff_heal = buff_heal
        self.buff_light = buff_light
        self.fuel = fuel
        self.hp = hp

    def interact(self, interlocutor):
        if interlocutor.name == "You":
            message("Picked up: " + self.describe(), color_ui_fuel)
            interlocutor.attack += self.buff_atk
            interlocutor.defense += self.buff_def
            interlocutor.heal += self.buff_heal
            interlocutor.torch_radius += self.buff_light
            if self.world.player.fuel + self.fuel > self.world.player.max_fuel:
                interlocutor.fuel += self.fuel
                interlocutor.hp += self.hp
            self.world.despawn_object(self)

    def describe(self):
        desc = self.description
        if self.buff_atk != 0:
            desc += " ATK: " + str(self.buff_atk)
        if self.buff_def != 0:
            desc += " DEF: " + str(self.buff_def)
        if self.buff_heal != 0:
            desc += " HEAL: " + str(self.buff_heal)
        if self.buff_light != 0:
            desc += " LIGHT: " + str(self.buff_light)
        if self.hp != 0:
            desc += " Health: " + str(self.hp)
        if self.fuel != 0:
            desc += " Fuel: " + str(self.fuel)
        return desc

class GameNPC(GameObject):
    def __init__(self, x, y, char, color, speed, hp, attack, defense, name="NPC", description="Not you.", ai_type = "passive"):
        super(GameNPC, self).__init__(x, y, char, color, name, description)
        self.speed = speed
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = defense
        self.ai_type = ai_type
        self.blocks = True
        self.passive_target_x = 0
        self.passive_target_y = 0

    def update(self, world):
        super(GameNPC, self).update(world)
        if self.hp <= 0:
            message(self.name + " died!")
            #Now give the player a buff for killing the enemy, maybe.
            if libtcod.random_get_int(0, 0, 100) < DROP_BUFF_CHANCE:
                if libtcod.random_get_int(0,0,100) < DROP_ATK_CHANCE:
                    self.world.player.attack += 1
                    message("You feel stronger.", color_ui_charge)
                if libtcod.random_get_int(0,0,100) < DROP_DEF_CHANCE:
                    self.world.player.defense += 1
                    message("You feel sturdier.", color_ui_charge)
                if libtcod.random_get_int(0,0,100) < DROP_HEAL_CHANCE:
                    self.world.player.hp = self.world.player.max_hp
                    message("You feel completely rejuvinated.", color_ui_charge)
                if libtcod.random_get_int(0,0,100) < DROP_LIGHT_CHANCE:
                    self.world.player.torch_radius += 1
                    message("Your flashlight shines a little brighter.", color_ui_charge)

            #Now remove us from whatever world we're in
            self.world.despawn_object(self)
        if (self.x == player.x and self.y == player.y):
            player.interact(self)
        if self.ai_type == "passive":
            if self.passive_target_x == 0 and self.passive_target_y == 0:
                #We don't have anywhere to go, so make somewhere to go
                target_is_free = 1
                self.passive_target_x = 0
                self.passive_target_y = 0
                while not target_is_free == 0: #Pick random locations until we have one
                    self.passive_target_x = libtcod.random_get_int(0,0,MAP_WIDTH - 1)
                    self.passive_target_y = libtcod.random_get_int(0,0,MAP_HEIGHT - 1)
                    (target_is_free, object) = world.is_blocked(self.passive_target_x,self.passive_target_y)

            else:
                if self.x == self.passive_target_x and self.y == self.passive_target_y:
                    self.passive_target = (0,0) #We got there, so we need a new target
                else:
                    self.move_towards(self.passive_target_x, self.passive_target_y, world)
        elif self.ai_type == "aggressive":
            if self.visible: #If we're visible, we can also see the player. TODO: Make this more robust.
                if self.distance(world.player) < -1:
                    self.move_away(world.player.x, world.player.y, world)
                else:
                    self.move_towards(world.player.x, world.player.y, world)
        elif self.ai_type == "nonsensical":
            #Pick a random direction to move
            roll = libtcod.random_get_int(0,0,4)
            if roll == 0:
                self.move(-1,0, world)
            elif roll == 1:
                self.move(1,0, world)
            elif roll == 2:
                self.move(0,-1, world)
            elif roll == 3:
                self.move(0,1, world)
            elif roll == 4:
                self.move(0,0, world)

    def interact(self, interlocutor):
        if interlocutor.name != "You":
            return #We're not interacting with the player for some reason. This is not good.
        #See if we hit the enemy
        attacker_hit_try = libtcod.random_get_int(0, 0, interlocutor.attack) + interlocutor.attack
        defender_dodge_try = libtcod.random_get_int(0, 0, self.defense) + self.defense
        hit_enemy = False
        damage_enemy = 0
        if (attacker_hit_try > defender_dodge_try):
            hit_enemy = True
            #See how much we damage the enemy
            damage_enemy = (attacker_hit_try - defender_dodge_try) + libtcod.random_get_int(0,0,interlocutor.attack)
        else:
            hit_enemy = False

        #Deal the damage and report
        if hit_enemy:
            self.hp -= damage_enemy
            message(interlocutor.name + " hit " + self.name + " for " + str(damage_enemy) + " hit points.", libtcod.green)
        else:
            message(interlocutor.name + " missed " + self.name + ".", color_ui_text)

    def move(self, dx, dy, world):
        """Move (dx,dy) from the current position, checking for collisions in world and out-of-bounding in world."""
        if (self.x + dx < 0) or (self.x + dx >= world.mapwidth) or (self.y + dy < 0) or (self.y + dy >= world.mapheight):
            debug("Object \"" + self.name + "\" hit the edge of the map.")
        else:
            (block_status, object_hit) = world.is_blocked(self.x + dx, self.y + dy) #Check for collisions to map tiles
            if block_status == 1:
                debug("Object \"" + self.name + "\" hit a wall.")
            elif block_status == 2:
                if not object_hit is self:
                    debug("Object \"" + self.name + "\" hit another object (" + object_hit.name + ").")
                    object_hit.interact(self)
            else: #If we reach here, we are OK to move.
                self.x += dx
                self.y += dy

class Player(GameObject):
    """A player. Can be moved around and such things."""
    def __init__(self, x, y, char, color, name="You", description="A somewhat battered @ sign."):
        super(Player, self).__init__(x, y, char, color, name, description)
        self.visible = True #Player is visible by default
        self.blocks = True
        self.speed = 1
        self.torch_radius = 10
        self.max_hp = 10
        self.hp = self.max_hp
        self.max_fuel = 50
        self.fuel = self.max_fuel / 2
        self.fuel_per_jump = 10
        self.charge = -1
        self.max_charge = 5
        self.attack = 2
        self.defense = 2
        self.heal = 0
        self.dead = False

    def describe(self):
        """Return the description of the object."""
        return self.description + " You control this. Go wild! Currently at X:" + str(self.x) + " Y:" + str(self.y)

    def interact(self, interlocutor):
        if interlocutor.name == "You":
            return #We're interacting with the player for some reason. This is not good.
        #See if we got hit
        attacker_hit_try = libtcod.random_get_int(0, 0, 5) + interlocutor.attack
        defender_dodge_try = libtcod.random_get_int(0, 0, 5) + self.defense
        hit_enemy = False
        damage_enemy = 0
        if (attacker_hit_try > defender_dodge_try):
            hit_enemy = True
            #See how much we damage the enemy
            damage_enemy = (attacker_hit_try - defender_dodge_try) + libtcod.random_get_int(0,0,interlocutor.attack)
        else:
            hit_enemy = False

        #Deal the damage and report
        if hit_enemy:
            self.hp -= damage_enemy
            message(interlocutor.name + " hit " + self.name + " for " + str(damage_enemy) + " hit points.", libtcod.green)
        else:
            message(interlocutor.name + " missed " + self.name + ".", color_ui_text)

    def update(self, world):
        #We should check collisions here, for objects
        if self.charge < self.max_charge:
            self.charge += 1
        if self.hp <= 0 and self.dead == False:
            self.dead = True
            message("#############################################", libtcod.red)
            message("#############################################", libtcod.red)
            message("#############################################", libtcod.red)
            message("YOU HAVE DIED, ALL HOPE FOR HUMANITY IS LOST.", libtcod.lighter_red)
            message("#############################################", libtcod.red)
            for i in range(CCON_HEIGHT - 6):
                message("#############################################", libtcod.red)

class Tile:
    """A map tile. The map is made up of a lot of these."""
    def __init__(self, blocked, block_sight = None):
        """By default, tiles that block movement also block sight."""
        if block_sight is None:
            block_sight = blocked #This way, if block_sight is overridden, the value will be preserved.
        self.block_sight = block_sight
        self.blocked = blocked
        self.explored = False
    def unblock(self):
        """Unblock this tile."""
        self.blocked = False
        self.block_sight = False
    def block(self):
        """Block this tile."""
        self.blocked = True
        self.block_sight = True
    def explore(self):
        """Set this tile as having been explored."""
        self.explored = True
    def unexplore(self):
        """Mark this tile as explored."""
        self.explored = False

class UIPanel(object):
    """A user interface panel capable of drawing text and bars.."""
    def __init__(self, console, height, width):
        self.console = console
        self.height = height
        self.width = width
        self.margin = 1
        self.vmargin = 2
        self.clear(color_blank)
    def add_bar(self, x, y, name, value, maximum, bar_color, back_color):
        """
        Draw a bar in this panel's buffer.
        :param x: Location in X
        :param y: Location in Y
        :param name: The bar's name, displayed in the bar.
        :param value: The bar's current value.
        :param maximum: The bar's maximum value.
        :param bar_color: The color of the filled portion of the bar
        :param back_color: The color of the background of the bar.
        :return: Nothing.
        """
        total_width = (self.width - (self.margin * 4)) #Compute the maximum length of the bar.
        current_width = int(float(value) / maximum * total_width) #Compute the length of the bar.

        if current_width > total_width:
            current_width = total_width

        #Render the bar's BG
        libtcod.console_set_default_background(self.console, back_color)
        libtcod.console_rect(self.console, x, y, total_width - 1, 1, False, libtcod.BKGND_SCREEN)

        #Render the bar's colored section
        libtcod.console_set_default_background(self.console, bar_color)
        if current_width > 0:
            libtcod.console_rect(self.console, x, y, current_width, 1, False, libtcod.BKGND_SCREEN)

        #Render text on the bar
        libtcod.console_set_default_foreground(self.console, color_ui_text)
        libtcod.console_print_ex(self.console, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER, name + ": " + str(value) + "/" + str(maximum))

    def add_text(self, x, y, text, back_color):
        """
        Draw a text in this panel's buffer.
        :param x: Location in X
        :param y: Location in Y
        :param name: The text to display.
        :param back_color: The background color for the text..
        :return: Nothing.
        """
        total_width = (self.width - (self.margin * 2)) #Compute the maximum length of the bar.

        #Render the BG
        libtcod.console_set_default_background(self.console, back_color)
        libtcod.console_rect(self.console, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

        #Render text
        libtcod.console_set_default_foreground(self.console, color_ui_text)
        libtcod.console_print_ex(self.console, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER, text)

    def clear(self, back_color):

        #Set the whole panel to the default background
        libtcod.console_set_default_background(self.console, back_color)
        for y in range(self.height - 1):
            for x in range(self.width - 1):
                libtcod.console_put_char_ex(self.console, x, y, ' ', color_dark_wall, color_dark_bg)




#Global functions
def handle_keys():
    """Block until the player presses a key, and then handle that key."""
    global recompute_fov, game_state, world
    key = libtcod.console_wait_for_keypress(True) #By waiting for keypress, we have a "turn-based" game
    if world.player.dead == True and not (game_state == "menu" or game_state == "cutscene"):
        game_state = "dead"

    if game_state == "dead":
        if key.vk == libtcod.KEY_ESCAPE:
            return "exit"
        else:
        	return "didn't take turn"

    if game_state == "playing":
        #Handle movement for the player
        if key.vk == libtcod.KEY_UP:
            world.player.move(0,-world.player.speed, world)
            recompute_fov = True #After we move, recompute the FoV
            return "took turn"
        elif key.vk == libtcod.KEY_DOWN:
            world.player.move(0,world.player.speed, world)
            recompute_fov = True #After we move, recompute the FoV
            return "took turn"
        elif key.vk == libtcod.KEY_LEFT:
            world.player.move(-world.player.speed,0, world)
            recompute_fov = True #After we move, recompute the FoV
            return "took turn"
        elif key.vk == libtcod.KEY_RIGHT:
            world.player.move(world.player.speed,0, world)
            recompute_fov = True #After we move, recompute the FoV
            return "took turn"
        elif key.vk == libtcod.KEY_CHAR:
            if key.c == ord('j'): #Player wants to jump
                if player.fuel >= player.fuel_per_jump:
                    world.player.fuel -= world.player.fuel_per_jump
                    message("You fire the FTL and appear a long way away.", libtcod.yellow)
                    #TODO: Make a proper jump function, with effect
                    world.clear(MCON)
                    world.clear_map(MCON)
                    libtcod.console_flush()
                    world = World()
                    world.spawn_player(player)
                    recompute_fov = True
                else:
                    message("You fire the FTL, but your fuel is insufficient!", libtcod.yellow)
        #Controls for exiting
        elif key.vk == libtcod.KEY_ESCAPE:
            return "exit"  #exit game
        elif key.vk == libtcod.KEY_SPACE:
            debug(world.player.describe())
            return "didn't take turn"
        else:
            return "didn't take turn"


def render_user_interface():
    """
    Add appropriate text and bars to the user interface and blit it into the root console
    :return: Nothing
    """
    current_ui_y = 0
    current_ui_y += uipanel.vmargin
    #Panel Title
    uipanel.add_text(uipanel.margin, current_ui_y, "RAPTOR", color_zero)
    current_ui_y += 1
    uipanel.add_text(uipanel.margin, current_ui_y, "D O W N", color_zero)
    current_ui_y += uipanel.vmargin
    #Health
    uipanel.add_bar(uipanel.margin, current_ui_y, "Hull", world.player.hp, world.player.max_hp, color_ui_health, color_zero)
    current_ui_y += uipanel.vmargin
    #Fuel
    uipanel.add_bar(uipanel.margin, current_ui_y, "Fuel", world.player.fuel, world.player.max_fuel, color_ui_fuel, color_zero)
    current_ui_y += uipanel.vmargin
    #Charge
    uipanel.add_bar(uipanel.margin, current_ui_y, "Charge", world.player.charge, world.player.max_charge, color_ui_charge, color_zero)
    current_ui_y += uipanel.vmargin
    #Countdown
    uipanel.add_bar(uipanel.margin, current_ui_y, "Time", world.countdown, COUNTDOWN_MAX, color_ui_countdown, color_zero)
    current_ui_y += uipanel.vmargin

    uipanel.add_text(uipanel.margin, current_ui_y, "------------------", color_zero)
    current_ui_y += uipanel.vmargin

    #Status
    if world.player.charge == world.player.max_charge and world.player.fuel > world.player.fuel_per_jump:
        uipanel.add_text(uipanel.margin, current_ui_y, "GO FOR JUMP", color_zero)
    else:
        uipanel.add_text(uipanel.margin, current_ui_y, "NO JUMP", color_zero)
    current_ui_y += 1

    #Show ATK, DEF, HEAL, and LIGHT
    uipanel.add_text(uipanel.margin, current_ui_y, "ATK: " + str(world.player.attack), color_zero)
    current_ui_y += 1
    uipanel.add_text(uipanel.margin, current_ui_y, "DEF: " + str(world.player.defense), color_zero)
    current_ui_y += 1
    uipanel.add_text(uipanel.margin, current_ui_y, "HEAL: " + str(world.player.heal), color_zero)
    current_ui_y += 1
    uipanel.add_text(uipanel.margin, current_ui_y, "LIGHT: " + str(world.player.torch_radius), color_zero)
    current_ui_y += 2

    uipanel.add_text(uipanel.margin, current_ui_y, "------------------", color_zero)
    current_ui_y += uipanel.vmargin

    #Description area

    #Blit onto the root console
    libtcod.console_blit(PCON, 0, 0, PCON_WIDTH, PCON_HEIGHT, RCON, SCREEN_WIDTH - int(SCREEN_WIDTH * 0.25) + 2, 1)

def clear_user_interface():
    """
    Clears the UI for rewriting.
    :return: Nothing.
    """
    uipanel.clear(color_blank)
    libtcod.console_blit(PCON, 0, 0, PCON_WIDTH, PCON_HEIGHT, RCON, SCREEN_WIDTH - int(SCREEN_WIDTH * 0.25) + 2, 1)

def message(new_msg, color = libtcod.white):
    #split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, CCON_WIDTH - 2)

    for line in new_msg_lines:
        #if the buffer is full, remove the first line to make room for the new one
        debug("CCON_HEIGHT: " + str(CCON_HEIGHT) + ", len(messages): " + str(len(messages)))
        if len(messages) == CCON_HEIGHT - 1:
            del messages[0]

        #add the new line as a tuple, with the text and the color
        messages.append( (line, color) )

def render_messages():
    #print the game messages, one line at a time
    y = 1
    for (line, color) in messages:
        libtcod.console_set_default_foreground(CCON, color)
        libtcod.console_print_ex(CCON, 1, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1
    #Blit onto the root console
    libtcod.console_blit(CCON, 0, 0, CCON_WIDTH, CCON_HEIGHT, RCON, 1, SCREEN_HEIGHT - int(SCREEN_HEIGHT * 0.25) + 2)

def clear_messages():
    #clear the game messages, one line at a time
    clearstring = ""
    for i in range(CCON_WIDTH - 1):
        clearstring += " "
    for y in range(CCON_HEIGHT):
        libtcod.console_set_default_foreground(CCON, color_zero)
        libtcod.console_print_ex(CCON, 1, y, libtcod.BKGND_NONE, libtcod.LEFT, clearstring)
    #Blit onto the root console
    libtcod.console_blit(CCON, 0, 0, CCON_WIDTH, CCON_HEIGHT, RCON, 1, SCREEN_HEIGHT - int(SCREEN_HEIGHT * 0.25) + 2)

#Main runtime execution starts here
#Init the screen
#Set a custom font
libtcod.console_set_custom_font('data/fonts/consolas12x12_gs_tc.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
#Console init
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, CONSOLE_TITLE, CONSOLE_FULLSCREEN)
#Set the FPS limit
libtcod.sys_set_fps(LIMIT_FPS)

#Init global variables
game_state = "playing"
status = "took turn"
#One of playing, cutscene, menu, dead
messages = []
world = World()
uipanel = UIPanel(PCON, PCON_HEIGHT, PCON_WIDTH)
player = Player(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', libtcod.white)
world.spawn_player(player)

recompute_fov = True #Do we need to recompute the field of view?

#Test object
message("Welcome to Raptor Down by Leo Tindall for Code Day San Diego.", color_ui_health)
message("Arrows to move, Space for menu, ESC exits", color_ui_text)
message("You are the @ sign. Enemies are colored letters. If the timer runs out, the Cylons will come, and you will be swarmed, so jump out of the level before then. Good luck!", color_ui_text)
world.spawn_object(GameObject(10, 14, '.', libtcod.green))

#Initial update
world.clear(MCON)
world.clear_map(MCON)
clear_messages()
libtcod.map_compute_fov(world.FOVMap, world.player.x, world.player.y, world.player.torch_radius, FOV_LIGHT_WALLS, FOV_ALGO)
while not libtcod.console_is_window_closed():
#Main loop
    #Initial time
    time_main_loop_start = int(round(time.time() * 1000)) #Time in millis
    #Perform AI
    if game_state == "playing" and status != "didn't take turn":
        world.update()
    #Draw everything into the buffer
    world.draw(MCON)
    #Blit the map onto the root console
    libtcod.console_blit(MCON, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, RCON, MCON_DRAW_OFFSET_X, MCON_DRAW_OFFSET_Y)
    #Draw the UI
    render_user_interface()
    render_messages()
    #Write changes out to screen
    libtcod.console_flush()
    #Now clear everything for the next frame.
    #This is happening in the buffer and not on the screen becuase we won't flush until the next loop.
    world.clear(MCON)
    if recompute_fov:
        recompute_fov = False
        world.clear_map(MCON) #Clear off the map so that once the FOV is updated and the map is redrawn, everything works right
        #Now recompute the FOV map
        libtcod.map_compute_fov(world.FOVMap, world.player.x, world.player.y, world.player.torch_radius, FOV_LIGHT_WALLS, FOV_ALGO)
    clear_user_interface()
    clear_messages()
    #Block until the player makes a decision and presses a key. Returns True if we need to exit.
    time_main_loop_end = int(round(time.time() * 1000)) #Time in millis
    #Final time
    #debug("Frame took: " + str(time_main_loop_end - time_main_loop_start) + " ms")
    status = handle_keys()
    if status == "exit":
        break

#End main loop
debug("Exiting cleanly.")
#Cleanup here
