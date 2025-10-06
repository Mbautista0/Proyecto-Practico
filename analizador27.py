# -*- coding: utf-8 -*-
"""
Created on Tue Sep 16 16:27:17 2025
"""

from __future__ import print_function
import json
import re
import os

# ============================================================
# LEXER
# ============================================================

class Tokenizer:
    """
    Analizador Lexico (Lexer)
    Convierte el texto de entrada en una secuencia de tokens.
    """
    def __init__(self, source_code):
        self.source = source_code
        self.tokens = []

    def _strip_inline_comments(self, line):
        """
        Elimina comentarios '#' al final de linea, pero respeta '#' dentro de "cadenas".
        Soporta escapes dentro de cadenas (\" y \\).
        """
        out = []
        in_str = False
        esc = False
        for ch in line:
            if in_str:
                if esc:
                    out.append(ch)
                    esc = False
                elif ch == '\\':
                    out.append(ch)
                    esc = True
                elif ch == '"':
                    out.append(ch)
                    in_str = False
                else:
                    out.append(ch)
            else:
                if ch == '"':
                    out.append(ch)
                    in_str = True
                elif ch == '#':
                   
                    break
                else:
                    out.append(ch)
        return ''.join(out).strip()

    def tokenize(self):
        lines = self.source.splitlines()
        for line in lines:
            line = line.rstrip('\n')
            line = self._strip_inline_comments(line)

            # Ignora lineas vacias (o de comentario)
            line = line.strip()
            if not line:
                continue

            
            regex_tokens = re.findall(r'"([^"]*)"|(\d+\.?\d*)|({|}|\[|\]|=|,|:)|(\w+)', line, flags=0)

            for group in regex_tokens:
                if group[0]:  # Cadena
                    self.tokens.append(('STRING', group[0]))
                elif group[1]:  # Número
                    if '.' in group[1]:
                        self.tokens.append(('NUMBER', float(group[1])))
                    else:
                        self.tokens.append(('NUMBER', int(group[1])))
                elif group[2]:  # Operador/delimitador
                    self.tokens.append(('OPERATOR', group[2]))
                elif group[3]:  # Identificador (incluye palabras clave)
                    self.tokens.append(('IDENTIFIER', group[3]))

        return self.tokens


# ============================================================
# PARSER
# ============================================================

class Parser:
    """
    Analizador Sintactico (Parser)
    Construye un AST/tabla de símbolos a partir de la secuencia de tokens.
    Gramática soportada:
      programa   := ( declaracion )*
      declaracion:= 'juego' STRING bloque
      bloque     := '{' ( seccion | asignacion )* '}'
      seccion    := IDENT '{' ... '}'
      asignacion := IDENT '=' valor
      valor      := NUMBER | STRING | TRUE/FALSE | lista | mapa
      lista      := '[' (valor (',' valor)*)? ']'
      mapa       := '{' (pares)* '}'     # acepta comas opcionales entre pares
      par        := (IDENT|STRING) (':'|'=') valor (',' opcional)
    """
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.symbol_table = {}

    # --------- utilidades ----------
    def get_token(self):
        if self.current_token_index < len(self.tokens):
            token = self.tokens[self.current_token_index]
            self.current_token_index += 1
            return token
        return None

    def peek_token(self, k=0):
        i = self.current_token_index + k
        if i < len(self.tokens):
            return self.tokens[i]
        return None

    def expect_operator(self, op_char):
        t = self.get_token()
        if not t or t[0] != 'OPERATOR' or t[1] != op_char:
            raise SyntaxError("Error de sintaxis: Se esperaba '%s', se encontro %s" % (op_char, (t and t[1])))
        return t

    def expect_kv_sep(self):
        """Acepta ':' o '=' como separador clave-valor dentro de mapas."""
        t = self.get_token()
        if not t or t[0] != 'OPERATOR' or t[1] not in (':', '='):
            raise SyntaxError("Error de sintaxis: Se esperaba ':' o '=', se encontro %s" % (t and t[1]))
        return t

    # --------- entrada principal ----------
    def parse(self):
        while self.peek_token() is not None:
            ident = self.peek_token()
            if not ident or ident[0] != 'IDENTIFIER':
                raise SyntaxError("Error de sintaxis: Se esperaba 'juego', se encontro %s" % (ident and ident[1]))
            if ident[1] != 'juego':
                raise SyntaxError("Error de sintaxis: Se esperaba 'juego', se encontro %s" % ident[1])

            
            self.get_token()

           
            name_tok = self.get_token()
            if not name_tok or name_tok[0] != 'STRING':
                raise SyntaxError("Error de sintaxis: Se esperaba un nombre de juego entre comillas")

            game_name = name_tok[1]

           
            root_block = self.parse_block_section()

            if game_name in self.symbol_table:
                raise SyntaxError("Error de sintaxis: El juego '%s' ya fue declarado" % game_name)

            self.symbol_table[game_name] = root_block

        return self.symbol_table

    # --------- bloques/secciones ----------
    def parse_block_section(self):
        self.expect_operator('{')
        block_content = {}

        while True:
            tok = self.peek_token()
            if tok is None:
                raise SyntaxError("Error de sintaxis: Falta '}' para cerrar el bloque")
            if tok[0] == 'OPERATOR' and tok[1] == '}':
                self.get_token()  
                break

            if tok[0] != 'IDENTIFIER':
                raise SyntaxError("Error de sintaxis en bloque: Se esperaba un identificador, se encontro %s" % tok[1])

            key_tok = self.get_token()  # IDENT
            next_tok = self.peek_token()

            if next_tok and next_tok[0] == 'OPERATOR' and next_tok[1] == '=':
               
                self.get_token() 
                value = self.parse_value()
                if key_tok[1] in block_content:
                    raise SyntaxError("Error: Redefinicion de clave '%s' en el mismo bloque" % key_tok[1])
                block_content[key_tok[1]] = value

            elif next_tok and next_tok[0] == 'OPERATOR' and next_tok[1] == '{':
                
                sub_block = self.parse_block_section()
                if key_tok[1] in block_content:
                    raise SyntaxError("Error: Redefinicion de seccion '%s' en el mismo bloque" % key_tok[1])
                block_content[key_tok[1]] = sub_block

            else:
                raise SyntaxError("Error de sintaxis: Tras '%s' se esperaba '=' o '{'" % key_tok[1])

        return block_content

    # --------- valores ----------
    def parse_value(self):
        token = self.peek_token()
        if token is None:
            raise SyntaxError("Error de sintaxis: Se esperaba un valor")

        ttype, tval = token

        if ttype == 'STRING':
            self.get_token()
            return tval
        if ttype == 'NUMBER':
            self.get_token()
            return tval
        if ttype == 'IDENTIFIER' and tval in ('verdadero', 'falso'):
            self.get_token()
            return True if tval == 'verdadero' else False

        if ttype == 'OPERATOR' and tval == '[':
            return self.parse_list()
        if ttype == 'OPERATOR' and tval == '{':
            return self.parse_map()

        raise SyntaxError("Error de sintaxis: Valor inesperado '%s'" % tval)

    def parse_list(self):
        self.expect_operator('[')
        lst = []

        while True:
            tok = self.peek_token()
            if tok is None:
                raise SyntaxError("Error de sintaxis: Falta ']' para cerrar la lista")
            if tok[0] == 'OPERATOR' and tok[1] == ']':
                self.get_token()  # consume ']'
                break

            
            if tok[0] == 'IDENTIFIER' and tok[1] not in ('verdadero', 'falso'):
                ref = self.get_token()[1]
                raise NameError("Error semantico: El identificador '%s' no ha sido definido como valor literal en listas." % ref)
            else:
                lst.append(self.parse_value())

            # coma opcional
            comma = self.peek_token()
            if comma and comma[0] == 'OPERATOR' and comma[1] == ',':
                self.get_token()  
        return lst

    def parse_map(self):
        """
        Acepta:
          - ':' o '=' como separador clave-valor
          - comas OPCIONALES entre pares
        """
        self.expect_operator('{')
        mp = {}

        while True:
            t = self.peek_token()
            if t is None:
                raise SyntaxError("Error de sintaxis: Falta '}' para cerrar el mapa")

            # cierre del mapa
            if t[0] == 'OPERATOR' and t[1] == '}':
                self.get_token()
                break

            # permitir coma opcional antes de la siguiente clave
            if t[0] == 'OPERATOR' and t[1] == ',':
                self.get_token()
                continue

            # clave
            if t[0] not in ('IDENTIFIER', 'STRING'):
                raise SyntaxError("Error de sintaxis: Clave invalida en mapa (usa IDENT o STRING), se encontro %s" % t[1])
            k = self.get_token()[1]

            # separador ':' o '='
            self.expect_kv_sep()

            # valor
            v = self.parse_value()

            if k in mp:
                raise SyntaxError("Error: Clave duplicada '%s' en mapa" % k)
            mp[k] = v
           

        return mp


# ============================================================
# VALIDACION MINIMA POR JUEGO
# ============================================================

try:
    long
except NameError:
    long = int

try:
    basestring
except NameError:
    basestring = (str,)

def is_int_strict(x):
    return isinstance(x, (int, long)) and not isinstance(x, bool)

def is_str(x):
    return isinstance(x, basestring)

def validate_snake(cfg):
    """
    Requisitos minimos:
      - secciones: rejilla, velocidad, controles
      - rejilla.ancho (int>0), rejilla.alto (int>0)
      - velocidad.tick_ms (int>0)
      - controles: arriba, abajo, izquierda, derecha (strings)
    """
    missing_sections = [k for k in ('rejilla','velocidad','controles') if k not in cfg]
    if missing_sections:
        return False, "Snake: faltan secciones: " + ", ".join(missing_sections)

    rej = cfg['rejilla']
    vel = cfg['velocidad']
    con = cfg['controles']

    if not (is_int_strict(rej.get('ancho')) and rej['ancho'] > 0):
        return False, "Snake: rejilla.ancho debe ser entero > 0"
    if not (is_int_strict(rej.get('alto')) and rej['alto'] > 0):
        return False, "Snake: rejilla.alto debe ser entero > 0"
    if not (is_int_strict(vel.get('tick_ms')) and vel['tick_ms'] > 0):
        return False, "Snake: velocidad.tick_ms debe ser entero > 0"

    for k in ('arriba','abajo','izquierda','derecha'):
        if not is_str(con.get(k)):
            return False, "Snake: controles.%s debe ser cadena" % k

    return True, "Snake OK"

def validate_tetris(cfg):
    """
    Requisitos minimos:
      - secciones: rejilla, velocidad, puntuacion
      - rejilla.ancho (int>0), rejilla.alto (int>0)
      - velocidad.gravedad_ms (int>0)
      - puntuacion.por_linea (mapa con llaves '1'..'4' y valores int>=0)
    """
    missing_sections = [k for k in ('rejilla','velocidad','puntuacion') if k not in cfg]
    if missing_sections:
        return False, "Tetris: faltan secciones: " + ", ".join(missing_sections)

    rej = cfg['rejilla']
    vel = cfg['velocidad']
    pun = cfg['puntuacion']

    if not (is_int_strict(rej.get('ancho')) and rej['ancho'] > 0):
        return False, "Tetris: rejilla.ancho debe ser entero > 0"
    if not (is_int_strict(rej.get('alto')) and rej['alto'] > 0):
        return False, "Tetris: rejilla.alto debe ser entero > 0"
    if not (is_int_strict(vel.get('gravedad_ms')) and vel['gravedad_ms'] > 0):
        return False, "Tetris: velocidad.gravedad_ms debe ser entero > 0"

    pl = pun.get('por_linea')
    if not isinstance(pl, dict):
        return False, "Tetris: puntuacion.por_linea debe ser un mapa"
    for k in ('1','2','3','4'):
        if k not in pl or not is_int_strict(pl[k]) or pl[k] < 0:
            return False, "Tetris: puntuacion.por_linea['%s'] debe ser entero >= 0" % k

    for opt in ('soft_drop_ms','lock_delay_ms'):
        if opt in vel and not is_int_strict(vel[opt]):
            return False, "Tetris: velocidad.%s debe ser entero" % opt

    return True, "Tetris OK"

def validate_all(symbol_table):
    """
    Recorre todos los juegos del archivo y retorna lista de resultados.
    """
    results = []
    for game_name, cfg in symbol_table.items():
        if game_name == 'snake':
            ok, msg = validate_snake(cfg)
        elif game_name == 'tetris':
            ok, msg = validate_tetris(cfg)
        else:
            ok, msg = True, "Juego generico (sin validador especifico)"
        results.append({'juego': game_name, 'valido': ok, 'mensaje': msg})
    return results


# ============================================================
# UTILIDADES DE ARCHIVO
# ============================================================

def load_file_content(file_path):
    if not os.path.exists(file_path):
        print("Error: El archivo '%s' no se encontro. Asegurate de que el archivo exista en la misma carpeta que el script." % file_path)
        return None

    with open(file_path, 'r') as file:
        return file.read()

def save_ast_to_file(ast, ast_file_path):
    try:
        with open(ast_file_path, 'w') as file:
            json.dump(ast, file, indent=4)
        print("AST guardado exitosamente en '%s'" % ast_file_path)
    except Exception as e:
        print("Error al guardar el archivo: %s" % e)


# ============================================================
# ZONA DE EJECUCION
# ============================================================

file_path = "snake.brik"   # o "tetris.brik"
ast_file_path = "arbol.ast"

source_code = load_file_content(file_path)

if source_code:
    print("--- Analisis Lexico (Lexer) ---")
    tokenizer = Tokenizer(source_code)
    tokens = tokenizer.tokenize()
    print("Tokens reconocidos:")
    for token in tokens:
        print(token)

    print("\n--- Analisis Sintactico (Parser) ---")
    parser = Parser(tokens)
    try:
        symbol_table = parser.parse()
        print("Sintaxis correcta. Se ha construido el AST/Tabla de Simbolos.")
        print("Contenido del AST (tabla de simbolos):")
        print(json.dumps(symbol_table, indent=4))

        # Guardar AST
        save_ast_to_file(symbol_table, ast_file_path)

        # Validacion
        print("\n--- Validacion ---")
        results = validate_all(symbol_table)
        print(json.dumps(results, indent=4))

    except (SyntaxError, NameError) as e:
        print("Error en la sintaxis: %s" % e)
