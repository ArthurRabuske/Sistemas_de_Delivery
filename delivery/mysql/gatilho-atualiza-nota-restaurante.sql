use eucomida;


DELIMITER //
CREATE TRIGGER atualiza_nota_restaurante
AFTER INSERT ON avaliacao
FOR EACH ROW
BEGIN
    DECLARE nova_nota DECIMAL(2,1);

    -- Calcula a média das notas do restaurante
    SELECT ROUND(AVG(nota), 1) INTO nova_nota
    FROM avaliacao
    WHERE id_restaurante = NEW.id_restaurante;

    -- Atualiza a média do restaurante
    UPDATE restaurante
    SET avaliacao = nova_nota
    WHERE id = NEW.id_restaurante;
END;
//

