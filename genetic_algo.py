import random as rnd
from enum import Enum
import msvcrt
import time 
import os
import copy
import sys
import traceback
import cProfile

GENERATIONS = 20
POPULATION_SIZE = 10
GRID_WIDTH  = 10
MID_WIDTH   = int(GRID_WIDTH * 0.5)

GRID_HIDDEN = 4
GRID_HEIGHT = 20 + GRID_HIDDEN

MUTATE_RATIO = 0.1
FITTEST_RATIO = 0.3

EMPTY = " "
BLOCK = "0"

TEST_GAMES = 100

DEBUG = False

def printd(_str):
    if (DEBUG):
        print(_str)


#****************** GAME STUFF ****************************

class ROTATION(Enum):
    CLOCKWISE = 4
    COUNTER_CLOCKWISE = 5
    NULL = 6

class MOVEMENT(Enum):
    MOVE_LEFT  = 1
    MOVE_RIGHT = 2
    MOVE_DOWN  = 3
    ROTATE_CLOCKWISE         = ROTATION.CLOCKWISE        
    ROTATE_COUNTER_CLOCKWISE = ROTATION.COUNTER_CLOCKWISE


class Coordinate:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return "Coordinate x: " + str(self.x) + " y: " + str(self.y)

class Matrix():
    def __init__(self, x, y):
        self.t_x = x
        self.t_y = y

    def __str__(self):
        return str((("t_x and t_y " + str((self.t_x, self.t_y)))))

    def inv_transform(self, coordinate):
        return Coordinate(coordinate.x - self.t_x, coordinate.y - self.t_y)

    def transform(self, coordinate):
        return Coordinate(coordinate.x + self.t_x, coordinate.y + self.t_y)

    def translate(self, coordinate):
        self.t_x += coordinate.x
        self.t_y += coordinate.y

    def translate_t(self, tuple):
        self.t_x += tuple[0]
        self.t_y += tuple[1]

class Shape:
    I = "I"
    O = "O"
    L = "L"
    T = "T"
    S = "S"
    S_2 = "S_2"
    L_2 = "L_2"
    
    shapes = { I : [["0", "0", "0", "0"]],

               O : [["0", "0"], ["0" , "0"]],

               L : [["0", " ", " "],
                    ["0", "0", "0"],],
               L_2 : [[" ", " ", "0"],
                    ["0", "0", "0"],],
               T : [[" ", "0", " "],
                    ["0", "0", "0"],],
               S : [["0", "0", " "],
                    [" ", "0", "0"]],
               S_2 : [["", "0", "0"],
                    ["0", "0", " "]],
                }

    def __init__(self, shapeID):
        self.rotations = 0
        self.shape   = self.shapes[shapeID]
        self.shapeID = shapeID
        self.anchor_point = Coordinate(0,0)
        self.matrix = Matrix(0,0)
        
        if shapeID == self.I:
            self.anchor_point = Coordinate(0, 1)
        elif shapeID == self.O:
            self.anchor_point = Coordinate(0, 0)
        elif shapeID == self.L:
            self.anchor_point = Coordinate(1, 1)
        elif shapeID == self.L_2:
            self.anchor_point = Coordinate(1, 1)
        elif shapeID == self.T:
            self.anchor_point = Coordinate(1, 1)
        elif shapeID == self.S:
            self.anchor_point = Coordinate(1, 1)
        elif shapeID == self.S_2:
            self.anchor_point = Coordinate(1, 1)

    def rotate(self, rotation = ROTATION.CLOCKWISE):
        if rotation == ROTATION.CLOCKWISE:
            self.rotations += 1
            if self.rotations == 37:
                traceback.print_stack()
        elif rotation == ROTATION.COUNTER_CLOCKWISE:
            self.rotations -= 1
        else:
            assert(False)

        diff_anchor = Coordinate(self.anchor_point.y - self.anchor_point.x, self.anchor_point.x - self.anchor_point.y)
        self.anchor_point = Coordinate(self.anchor_point.y, self.anchor_point.x)
        rotated_shape = []
        for y in range(len(self.shape[0])):
            temp = []
            for x in range(len(self.shape)):
                temp.append(self.shape[x][y])
            if rotation == ROTATION.CLOCKWISE:
                temp.reverse()
            rotated_shape.append(temp)
        if rotation == ROTATION.COUNTER_CLOCKWISE:
            rotated_shape.reverse()
        self.shape = rotated_shape
        self.matrix.translate(diff_anchor)
    
    def width(self):
        return len(self.shape[0])

    def h_width(self):
        return int (0.5 * self.width())

    def height(self):
        return len(self.shape)

    def get_random():
        shape = Shape(list(Shape.shapes.keys())[rnd.randrange(len(Shape.shapes))])
        for a in range(rnd.randrange(0,2)):
            shape.rotate()
        return shape

    def get(self, x, y):
        assert(x >= 0 and x < self.width())
        assert(y >= 0 and y < self.height())
        return self.shape[y][x]

    def get_local(self, x, y):
        (x, y) = self.matrix.inv_transform(x, y)
        return self.get(x, y)

    def current_position(self):
        return self.matrix.transform(Coordinate(0, 0))

    def print(self):
        for x in range(self.width()):
            for y in range(self.height()):
                print(self.get(x, y), end="")
            print()

class Game:
    def __init__(self):
        self.pieces = 1
        self.score = 0 
        self.iteration = 0
        self.piece = Shape.get_random()
        self.next_piece = Shape.get_random()
        self.movements = []
        self.score = 0
        self.is_game_over = False
        self.grid = []
        for y in range(GRID_HEIGHT):
            self.grid.append([" "] * GRID_WIDTH)
        
        assert(self._try_translate(self.get_start_pos(self.piece)))
        self._move_active_piece(self.get_start_pos(self.piece))

    def print(self, show_piece = False):
        to_print = ""
        to_print += " "
        for line in range(len(self.grid[GRID_HIDDEN:][0])):
            to_print += "_"
        to_print += "\n"
        for line in self.grid[GRID_HIDDEN:]:
            to_print += "|"
            for _char in line:
                to_print += _char
            to_print += "|\n"

        to_print += ("SCORE: " + str(self.score) + "\n")
        to_print += ("Next piece\n")
        for x in range(self.next_piece.width()):
            to_print += ("      ")
            for y in range(self.next_piece.height()):
                to_print += (self.next_piece.get(x, y))
            to_print += "\n"
        to_print += "-\n"
        print (to_print)

    def get_shape(self, shapeID):
        return self.shapes[shapeID]

    def width(self):
        return len(self.grid[0])

    def height(self):
        return len(self.grid)

    def delete_row(self, row_number):
        assert(row_number >= 0)
        assert(row_number < GRID_HEIGHT)
        for y in reversed(range(1, row_number + 1)):
            for x in range(self.width()):
                self.set(x, y, self.get(x, y - 1))

    def detect_and_remove_rows(self):
        is_filled = True
        for y in range(self.height()):
            is_filled = True
            for x in range(self.width()):
                if (self.get(x, y) == EMPTY):
                    is_filled = False
            if is_filled:
                self.delete_row(y)
                self.score += 1

    def collides(self, copy_grid, p_piece):
        for dx in range(p_piece.width()):
            for dy in range(p_piece.height()):
                pos = p_piece.matrix.transform(Coordinate(dx, dy))
                if pos.x < 0:
                    printd("too left")
                    return False
                if pos.y < 0:
                    assert(False)
                    return False
                if pos.x >= GRID_WIDTH:
                    printd("too right")
                    return False
                if pos.y >= GRID_HEIGHT:
                    printd("too low")
                    return False
                if (p_piece.get(dx, dy) == BLOCK and copy_grid[pos.y][pos.x] == BLOCK):
                    printd("another block")
                    return False
        return True

    def get_grid_without_piece(self):
        copy_grid = copy.deepcopy(self.grid)
        for dx in range(self.piece.width()):
            for dy in range(self.piece.height()):
                pos = self.piece.matrix.transform(Coordinate(dx, dy))
                if (self.piece.get(dx, dy) == BLOCK):
                    copy_grid[pos.y][pos.x] = EMPTY
        return copy_grid

    def is_empty_line(self, y):
        for x in range(self.width()):
            if x == BLOCK:
                return False
        return True

    def is_full_line(self, y):
        for x in range(self.width()):
            if self.get(x, y) == EMPTY:
                return False
        return True

    def get_clear_height(self):
        r = 0
        for y in self.height():
            if is_empty_line(y):
                r += 1
            else:
                return r
        return r

    def get_full_lines(self):
        count = 0
        for y in range(self.height()):
            if self.is_full_line(y):
                count += 1
        return count

    def get_holes(self):
        count = 0;
        for x in range(self.width()):
            block = False;
            for y in range(self.height()):
                if self.get(x, y) == BLOCK:
                    block = True
                elif self.get(x, y) == EMPTY and block:
                    count+=1
        return count


    def column_height(self, x):
        r = 0
        for y in range(self.height()):
            if (self.get(x, y) == BLOCK):
                break
            else:
                r+=1
        return self.height() - r
    
    def get_aggregate_height(self):
        total = 0
        for x in range(self.width()):
            total += self.column_height(x)
        return total;

    def bumpiness(self):
        total = 0;
        for x in range(self.width() - 1):
            total += abs(self.column_height(x) - self.column_height(x + 1));
        return total;

    def _try_rotate(self, rotation):
        p_piece = copy.deepcopy(self.piece)
        copy_grid = self.get_grid_without_piece()
        p_piece.rotate(rotation)
        return self.collides(copy_grid, p_piece);

    def _try_translate(self, diff):
        p_piece   = copy.deepcopy(self.piece)
        copy_grid = self.get_grid_without_piece()
        p_piece.matrix.translate_t(diff)
        # edges
        return self.collides(copy_grid, p_piece);

    def get(self, x, y):
        return self.grid[y][x]

    def fset(self, x, y, stuff):
        if (y < 0):
            # in this case it might be a start problem 
            # the I shape object if rotated might be over the top of the
            # grid
            return
        self.grid[y][x] = stuff

    def set(self, x, y, stuff):
        assert(stuff == EMPTY or stuff == BLOCK)
        assert(x >= 0)
        if (y < 0):
            # in this case it might be a start problem 
            # the I shape object if rotated might be over the top of the
            # grid
            return
        assert(x < self.width())
        assert(y < self.height())
        #if (stuff == EMPTY and x == 1 and (y == GRID_HEIGHT - 1)):
        #    print(self.piece.matrix)
        #    printd("trying to empty " + str(x) + " " + str(y))
        #    traceback.print_stack()
        #    self.grid[y][x] = "*"
        #    self.print()
        #    sys.exit()
        self.grid[y][x] = stuff

    def clear_active_piece(self):
        #erase
        for x in range(self.piece.width()):
            for y in range(self.piece.height()):
                t = self.piece.matrix.transform(Coordinate(x, y))
                if (t.y < 0):
                    pass
                if (self.piece.get(x, y) == BLOCK):
                    self.fset(t.x, t.y, EMPTY)

    def clear(self):
        for x in range(self.width()):
            for y in range(self.height()):
                self.fset(x, y, EMPTY)

    def paint_piece(self, like=BLOCK):
        for x in range(self.piece.width()):
            for y in range(self.piece.height()):
                t = self.piece.matrix.transform(Coordinate(x, y))
                if (self.piece.get(x, y) == BLOCK):
                    self.fset(t.x, t.y, like)

    def _move_active_piece(self, diff):
        #erase
        self.clear_active_piece()
        self.piece.matrix.translate_t(diff)
        self.paint_piece()

    def _rotate_active_piece(self, rotation):
        #erase
        self.clear_active_piece()
        self.piece.rotate(rotation)
        self.paint_piece()

    def reset(self):
        self.grid = []
        for y in range(GRID_HEIGHT):
            self.grid.append([" "] * GRID_WIDTH)

    def try_move(self, movement):
        if (movement == MOVEMENT.MOVE_LEFT):
            return self._try_translate((-1,0))
        elif (movement == MOVEMENT.MOVE_RIGHT):
            return self._try_translate((1,0))
        elif (movement == MOVEMENT.MOVE_DOWN):
            return self._try_translate((0,1))
        elif (movement == MOVEMENT.ROTATE_CLOCKWISE):
            return self._try_rotate(ROTATION.CLOCKWISE)
        elif (movement == MOVEMENT.ROTATE_COUNTER_CLOCKWISE):
            return self._try_rotate(ROTATION.COUNTER_CLOCKWISE)
    
    def move_back(self, amount=1):
        for i in range(amount):
            movement = movements.pop()
            if (movement == MOVEMENT.MOVE_LEFT):
                assert(self._try_translate((1,0)))
                self._move_active_piece((1,0))
            elif (movement == MOVEMENT.MOVE_RIGHT):
                assert(self._try_translate((-1,0)))
                self._move_active_piece((-1,0))
            elif (movement == MOVEMENT.MOVE_DOWN):
                assert(self._try_translate((0,-1)))
                self._move_active_piece((0,-1))
            elif (movement == MOVEMENT.ROTATE_CLOCKWISE):
                assert(self._try_rotate(ROTATION.COUNTER_CLOCKWISE))
                self._rotate_active_piece(ROTATION.COUNTER_CLOCKWISE)
            elif (movement == MOVEMENT.ROTATE_COUNTER_CLOCKWISE):
                assert(self._try_rotate(ROTATION.CLOCKWISE))
                self._rotate_active_piece(ROTATION.CLOCKWISE)

    def move(self, movement):
        if (movement == MOVEMENT.MOVE_LEFT):
            if(self._try_translate((-1,0))):
                self.movements.append(MOVEMENT.MOVE_LEFT)
                self._move_active_piece((-1,0))
        elif (movement == MOVEMENT.MOVE_RIGHT):
            if(self._try_translate((1,0))):
                self.movements.append(MOVEMENT.MOVE_RIGHT)
                self._move_active_piece((1,0))
        elif (movement == MOVEMENT.MOVE_DOWN):
            if(self._try_translate((0,1))):
                self.movements.append(MOVEMENT.MOVE_DOWN)
                self._move_active_piece((0,1))
        elif (movement == MOVEMENT.ROTATE_CLOCKWISE):
            if(self._try_rotate(ROTATION.CLOCKWISE)):
                self.movements.append(MOVEMENT.ROTATE_CLOCKWISE)
                self._rotate_active_piece(ROTATION.CLOCKWISE)
        elif (movement == MOVEMENT.ROTATE_COUNTER_CLOCKWISE):
            if(self._try_rotate(ROTATION.COUNTER_CLOCKWISE)):
                self.movements.append(MOVEMENT.ROTATE_COUNTER_CLOCKWISE)
                self._rotate_active_piece(ROTATION.COUNTER_CLOCKWISE)

    def get_start_pos(self, piece):
        return (MID_WIDTH - self.piece.h_width(), GRID_HIDDEN)

    # returns true if switched piece
    def push_down_by_clock(self):
        #if can't move further down
        if (self._try_translate((0,1)) == False):
            self.piece = copy.deepcopy(self.next_piece)
            self.next_piece = Shape.get_random()
            self.pieces += 1
            self.detect_and_remove_rows()
            #push down a lil bit the next piece
            if (self._try_translate(self.get_start_pos(self.piece)) == False):
                self.is_game_over = True
            else:
                self._move_active_piece(self.get_start_pos(self.piece))
            return True
        else:
            self._move_active_piece((0,1))

        return False

    def clone(self):
        return copy.deepcopy(self)

#****************** ALGO GENE STUFF ***********************
def random_choose(a, b):
    rnd.randrange(0, 2)
class Gene:
    def __init__(self, mutation=True):
        self.fit_score    = (0,0)
        self.heights_factor   = 0.7255915476593505
        self.lines_factor     = 1.1750264043234963
        self.holes_factor     = 0.083118520061818092
        self.bumpiness_factor = 0.6045332007969104
        if mutation:
            self.mutate(0.1)

    def score(self, game):
        _to_return =  -self.heights_factor    * game.get_aggregate_height()
        _to_return += self.lines_factor       * game.get_full_lines()
        _to_return += -self.holes_factor      * game.get_holes()
        _to_return += - self.bumpiness_factor * game.bumpiness()
        return _to_return

    def avg_score(self):
        return self.fit_score[1] / self.fit_score[0]

    def breed(self, father, mother):
        self.fit_score    = (0,0)
        self.heights_factor   = rnd.choice([father.heights_factor, mother.heights_factor])
        self.lines_factor     = rnd.choice([father.lines_factor, mother.lines_factor])
        self.holes_factor     = rnd.choice([father.holes_factor, mother.holes_factor])
        self.bumpiness_factor = rnd.choice([father.bumpiness_factor, mother.bumpiness_factor])

    def mutate(self, mutate_ratio):
        self.heights_factor   += rnd.uniform(-mutate_ratio, mutate_ratio)
        self.lines_factor     += rnd.uniform(-mutate_ratio, mutate_ratio)
        self.holes_factor     += rnd.uniform(-mutate_ratio, mutate_ratio)
        self.bumpiness_factor += rnd.uniform(-mutate_ratio, mutate_ratio)

    def print(self):
        print ("heights_factor: " + str(self.heights_factor))
        print ("lines_factor: " + str(self.lines_factor))
        print ("holes_factor: " + str(self.holes_factor))
        print ("bumpiness_factor: " + str(self.bumpiness_factor))


def init_genomes(population_size):
    population = []
    for i in range(population_size):
        population = population + [Gene()]
    return population

#def get_best_moves(game, gene):
#    return 


def get_best_moves(game, gene):
    start_i = len(game.movements)
    best_piece = (game.piece, -11011010.0, game.movements)
    state  =  game.clone()
    while (state.try_move(MOVEMENT.MOVE_LEFT)):
        state.move(MOVEMENT.MOVE_LEFT)

    it = state.clone()
    while it.try_move(MOVEMENT.MOVE_RIGHT):
        state_1 = it.clone()
        for rotation in range(4):
            for _i_ in range(rotation):
                if state_1.try_move(MOVEMENT.ROTATE_CLOCKWISE):
                    state_1.move(MOVEMENT.ROTATE_CLOCKWISE)
            state_2 = state_1.clone()
            while True:
                state_3 = state_2.clone()
                while state_3.try_move(MOVEMENT.MOVE_DOWN):
                    state_3.move(MOVEMENT.MOVE_DOWN)

                if gene.score(state_3) > best_piece[1]:
                    best_piece = (copy.deepcopy(state_3.piece), gene.score(state_3), state_3.movements)
                if state_2.try_move(MOVEMENT.MOVE_RIGHT) == False:
                    break
                state_2.move(MOVEMENT.MOVE_RIGHT)
        it.move(MOVEMENT.MOVE_RIGHT)
    
    return (best_piece[0], best_piece[2][start_i:])

# good seed
#heights_factor:   0.5255915476593505
#lines_factor:     1.090264043234963
#holes_factor:     0.003118520061818092
#bumpiness_factor: 0.6045332007969104

def survival_of_the_fittest(population):
    print ("******survival_of_the_fittest******")
    population.sort(key=lambda x: x.avg_score(), reverse=True)
    population[0].print()
    number_of_accepted_genes = int(FITTEST_RATIO * len(population))
    elite = population[:number_of_accepted_genes]
    next_population = copy.deepcopy(elite)
    for i in range(len(next_population)):
        next_population[i].fit_score = (0, 0)
    while len(next_population) < POPULATION_SIZE:
        father = rnd.choice(elite)
        mother = rnd.choice(elite)
        child  = Gene()
        child.breed(father, mother)
        child.mutate(MUTATE_RATIO)
        next_population.append(child)
    return next_population

def train():
    population = []
    #populate
    for i in range(POPULATION_SIZE):
        population.append(Gene())
    for generation_cycle in range(GENERATIONS):
        print("simulating...")
        for gene in population:
            for _a_ in range(1):
                total = "*" * int(10 * (_a_/TEST_GAMES))
                total = total + ((10 - len(total)) * "-")
                print (total, end="\r")
                game = Game()
                while (not game.is_game_over) and game.pieces < 300:
                    best_moves = get_best_moves(game, gene)
                    moves = best_moves[1]
                    moves.reverse()
                    while len(moves) > 0:
                        move = moves.pop()
                        assert(game.try_move(move))
                        game.move(move)
                    while game.push_down_by_clock() is not True:
                        pass
                gene.fit_score = (game.pieces + gene.fit_score[0], game.score + gene.fit_score[1])
        print("******* GEN " + str(generation_cycle + 1) + " RESULTS **********")
        for gene in population:
            print (gene.avg_score())
        population = survival_of_the_fittest(population)
                        
#****************** MAIN STUFF ****************************

def capture_input():
    if (msvcrt.kbhit()):
        _input = msvcrt.getch()
        if _input.upper() == b'A':
            return MOVEMENT.MOVE_LEFT
        elif _input.upper() == b'D':
            return MOVEMENT.MOVE_RIGHT
        if _input.upper() == b'S':
            return MOVEMENT.MOVE_DOWN
        if _input.upper() == b'Q':
            return MOVEMENT.ROTATE_COUNTER_CLOCKWISE
        elif _input.upper() == b'E':
            return MOVEMENT.ROTATE_CLOCKWISE
    return None

def clear_screen():
    pass
    #os.system("clear")

def main():
    game = Game()
    while not game.is_game_over:
        for i in range(10):
            movement = capture_input()
            if movement is not None:
                game.move(movement)
            game.print()
            time.sleep(.1)
        game.push_down_by_clock()
        game.print()

def ai_play():
    game = Game()
    ai = Gene(False)
    movements = get_best_moves(game, ai)[1]
    movements.reverse()
    while not game.is_game_over:
        for i in range(10):
            if len(movements) > 0:
                game.move(movements.pop())
            game.print()
            time.sleep(.1)
        if game.push_down_by_clock():
            movements = get_best_moves(game, ai)[1]
            movements.reverse()
        game.print()

#train()
#main()
ai_play()