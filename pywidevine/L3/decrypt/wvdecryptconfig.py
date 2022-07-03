import config as toolcfg

class WvDecryptConfig(object):
    def __init__(self, args, content, filename, tracktype, audio_only, trackno, license_, init_data_b64, cert_data_b64=None):
        self.args = args
        self.content = content
        self.filename = filename
        self.tracktype = tracktype
        self.audio_only = audio_only
        self.trackno = trackno
        self.init_data_b64 = init_data_b64
        self.license = license_
        if cert_data_b64 is not None:
            self.server_cert_required = True
            self.cert_data_b64 = cert_data_b64
        else:
            self.server_cert_required = False

    def get_filename(self, unformatted_filename):
        if self.tracktype == 'video':
            return unformatted_filename.format(filename=self.filename, track_type='video', track_no='0')
        else:
            return unformatted_filename.format(filename=self.filename, track_type='audio', track_no='0')

    def build_commandline_list(self, keys):
        if self.args.mp4_decrypt:
            commandline = [toolcfg.binaries.mp4decrypt]
            commandline.append('--show-progress')
            for key in keys:
                if key.type == 'CONTENT':
                    commandline.append('--key')
                    default_KID = 1
                    commandline.append('{}:{}'.format(str(default_KID), key.key.hex()))
            if self.tracktype == 'video':
                commandline.append(self.get_filename(toolcfg.filenames.encrypted_filename_video))
                commandline.append(self.get_filename(toolcfg.filenames.decrypted_filename_video))
            elif self.tracktype == 'audio':
                out_dec_filename = toolcfg.filenames.decrypted_filename_audio if not self.audio_only \
                    else toolcfg.filenames.decrypted_filename_audio_ff
                commandline.append(self.get_filename(toolcfg.filenames.encrypted_filename_audio))
                commandline.append(self.get_filename(out_dec_filename))
        else:
            commandline = [toolcfg.binaries.shaka]
            commandline.append('-quiet')
            key_id = '00000000000000000000000000000000'
            if self.tracktype == 'video':
                commandline.append('in={input},stream={stream},output={output},drm_label={drm_label}'.format(
                    input=self.get_filename(toolcfg.filenames.encrypted_filename_video),
                    stream='video',
                    output=self.get_filename(toolcfg.filenames.decrypted_filename_video),
                    drm_label='UHD1'))
                commandline.append('--enable_raw_key_decryption')
                for key in keys:
                    if key.type == 'CONTENT':
                        if self.content != 'music-video':
                            key_id = key.kid.hex()
                        commandline.append('--keys')
                        commandline.append('label=UHD1:key_id={kid}:key={key}'.format(
                            key=key.key.hex(),
                            kid=key_id))

            elif self.tracktype == 'audio':
                out_dec_filename = toolcfg.filenames.decrypted_filename_audio if not self.audio_only \
                    else toolcfg.filenames.decrypted_filename_audio_ff

                commandline.append('in={input},stream={stream},output={output},drm_label={drm_label}'.format(
                    input=self.get_filename(toolcfg.filenames.encrypted_filename_audio),
                    stream='audio',
                    output=self.get_filename(out_dec_filename),
                    drm_label='HD'))
                commandline.append('--enable_raw_key_decryption')
                for key in keys:
                    if key.type == 'CONTENT':
                        if self.content != 'music-video':
                            key_id = key.kid.hex()
                        commandline.append('--keys')
                        commandline.append('label=HD:key_id={kid}:key={key}'.format(
                            key=key.key.hex(), kid=key_id))
        #~ print(commandline)
        #~ input()
        return commandline