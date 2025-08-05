# En tu_app/parsers.py

import json
import re
from rest_framework.parsers import BaseParser
from rest_framework.exceptions import ParseError


class MixedReplaceParser(BaseParser):
    """
    Parser para el content type no estándar 'multipart/x-mixed-replace'.

    Este parser asume que dentro del cuerpo multipart hay un único
    bloque de texto JSON que necesita ser extraído.
    """
    media_type = 'multipart/x-mixed-replace'

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Lee el stream de la petición, extrae el JSON y lo retorna.
        """
        # Lee el cuerpo completo de la petición
        body_bytes = stream.read()

        try:
            # Decodifica el cuerpo de bytes a un string
            body_str = body_bytes.decode('utf-8')
        except UnicodeDecodeError:
            raise ParseError('Codificación de la petición inválida. Se esperaba UTF-8.')

        # Usa una expresión regular para encontrar el contenido JSON.
        # Busca el primer '{' hasta el último '}'
        json_match = re.search(r'\{.*\}', body_str, re.DOTALL)

        if not json_match:
            raise ParseError('No se encontró un bloque de JSON válido en la petición.')

        json_str = json_match.group(0)

        # Intenta convertir el string extraído a un diccionario de Python
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            raise ParseError('JSON mal formado.')