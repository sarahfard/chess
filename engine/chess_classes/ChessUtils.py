# -*- coding: utf-8 -*-

def build_official_move(move_data):


    if move_data['rook']:
        res = move_data['rook']
    else:
        res_piece_name = ''
        if move_data['source_piece'].role.name != 'P':
            res_piece_name = move_data['source_piece'].role.name
        res_source_coords = '%s%s' % (move_data['src_x'], move_data['src_y'])
        res_catch = '-'
        if move_data['target_piece'] != '-' or move_data['ep']:
            res_catch = 'x'
        res_target_coords = '%s%s' % (move_data['dest_x'], move_data['dest_y'])
        res_ep = ''
        if move_data['ep']:
            res_ep = 'ep'
        res_promo = ''
        if move_data['promo']:
            res_promo = move_data['promo']['r']
        res_check = ''
        if move_data['check']:
            if move_data['check'] == 'check':
                res_check = '+'
            elif move_data['check'] == 'checkmate':
                res_check = '#'

        res = '{piece_name}{source_coords}{catch}{target_coords}{ep}{promo}{check}'.format(
                piece_name=res_piece_name, source_coords=res_source_coords, catch=res_catch,
                target_coords=res_target_coords, ep=res_ep, promo=res_promo, check=res_check
        )
    return res
