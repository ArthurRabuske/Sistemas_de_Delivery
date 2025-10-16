    
    -- Se o produto estiver inativo, impedir a inserção
DELIMITER //

CREATE TRIGGER before_insert_item_pedido
BEFORE INSERT ON item_pedido
FOR EACH ROW
BEGIN
    DECLARE produto_status VARCHAR(10);
    
    -- Verificar o status do produto
    SELECT stats INTO produto_status
    FROM produto 
    WHERE id = NEW.id_produto;
    
    -- Se o produto estiver inativo, impedir a inserção
    IF produto_status = 'inativo' THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Não é possível adicionar produto inativo ao pedido';
    END IF;
END//

DELIMITER ;